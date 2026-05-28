package nero.router

import org.scalatest.funspec.AnyFunSpec

import circt.stage.ChiselStage

import chisel3._
import chisel3.util.random.MaxPeriodGaloisLFSR
import chisel3.util._
import chisel3.util.experimental.BoringUtils
import chisel3.probe.read
import chisel3.simulator.scalatest.ChiselSim
import chisel3.simulator.stimulus.RunUntilFinished
import chisel3.simulator.HasSimulator
import chisel3.layer._

import nero.parameters.NeroParameters
import nero.bundle.AXISBundle
import nero.util._

private class AXISPacketFuzzer(seed: Int, param: NeroParameters)
    extends Module {
  val io = IO(new AXISBundle(param))

  private class PosEdgeDetector extends Module {
    val io = IO(new Bundle {
      val in = Input(Bool())
      val out = Output(Bool())
    })

    val prev = RegNext(io.in, false.B)
    io.out := io.in && !prev
  }

  val controlLFSR = Module(new MaxPeriodGaloisLFSR(8, Some(seed)))
  val dataLFSR = Module(new MaxPeriodGaloisLFSR(16, Some(seed)))

  val valid = RegInit(false.B)
  val data = RegInit(0.U(param.totalWireWidth.W))

  io.payload.valid := valid
  io.payload.bits.src.x := data(1, 0)
  io.payload.bits.src.y := data(3, 2)
  io.payload.bits.dest.x := data(5, 4)
  io.payload.bits.dest.y := data(7, 6)
  io.payload.bits.local.x := data(8)
  io.payload.bits.local.y := data(9)
  io.payload.bits.timestamp := 0.U

  // Both LFSR always increments.
  controlLFSR.io.increment := true.B
  controlLFSR.io.seed.valid := false.B
  controlLFSR.io.seed.bits := DontCare

  dataLFSR.io.increment := true.B
  dataLFSR.io.seed.valid := false.B
  dataLFSR.io.seed.bits := DontCare

  val shouldTransition = controlLFSR.io.out(0)
  when(valid === false.B) {
    valid := shouldTransition
  }.otherwise {
    when(io.payload.fire) {
      valid := shouldTransition
    }
  }

  when(io.payload.fire) {
    data := dataLFSR.io.out.asUInt
  }

  block(VerbosePrint) {
    val edgeDetector = Module(new PosEdgeDetector)
    edgeDetector.io.in := io.payload.valid

    when(edgeDetector.io.out | io.payload.fire) {
      val payload = io.payload.bits
      printf(
        cf"[$SimulationTime] $HierarchicalModuleName VALID asserted\n"
      )
    }
  }
}

private class AXISPacketReceiver(seed: Int, param: NeroParameters)
    extends Module {
  val io = IO(Flipped(new AXISBundle(param)))

  val controlLFSR = Module(new MaxPeriodGaloisLFSR(8, Some(seed)))

  val watchdog = new Counter(1026)
  val previousData = RegInit(0.U(param.totalWireWidth.W))
  val previousValid = RegInit(false.B)
  val previousFire = RegInit(false.B)

  val incomingData = Cat(
    io.payload.bits.local.y,
    io.payload.bits.local.x,
    io.payload.bits.dest.y,
    io.payload.bits.dest.x,
    io.payload.bits.src.y,
    io.payload.bits.src.x
  )
  previousData := incomingData
  previousValid := io.payload.valid
  previousFire := io.payload.fire

  val canAssertReady = controlLFSR.io.out(0)
  io.payload.ready := canAssertReady

  controlLFSR.io.increment := true.B
  controlLFSR.io.seed.valid := false.B
  controlLFSR.io.seed.bits := DontCare

  val isDataStable = previousData === incomingData

  when(previousValid && !previousFire) {
    assert(
      io.payload.valid,
      "TVALID got deasserted while TREADY is not asserted yet."
    )
    assert(
      isDataStable,
      cf"TDATA was changed while VALID is asserted. Previous: $previousData%b, Current: $incomingData%b"
    )
  }

  when(io.payload.fire) {
    watchdog.reset()
  }.otherwise {
    watchdog.inc()
  }

  assert(
    watchdog.value <= 1024.U,
    "Watchdog timeout: no packets were recevied for 1,024 cycles"
  )

  block(VerbosePrint) {
    when(io.payload.fire) {
      val payload = io.payload.bits
      printf(
        cf"[$SimulationTime] $HierarchicalModuleName transaction received with payload:\n" +
          cf"$payload"
      )
    }
  }
}

private class AXISRouterTestHarness(seed: Int, param: NeroParameters)
    extends Module {
  val fuzzers = Seq.tabulate(8)(f => Module(new AXISPacketFuzzer(seed, param)))
  val receivers =
    Seq.tabulate(8)(f => Module(new AXISPacketReceiver(seed, param)))
  val router = Module(new Router(param))

  router.northInbound :<>= fuzzers(0).io
  router.eastInbound :<>= fuzzers(1).io
  router.westInbound :<>= fuzzers(2).io
  router.southInbound :<>= fuzzers(3).io
  router.local0Inbound :<>= fuzzers(4).io
  router.local1Inbound :<>= fuzzers(5).io
  router.local2Inbound :<>= fuzzers(6).io
  router.local3Inbound :<>= fuzzers(7).io

  receivers(0).io :<>= router.northOutbound
  receivers(1).io :<>= router.eastOutbound
  receivers(2).io :<>= router.westOutbound
  receivers(3).io :<>= router.southOutbound
  receivers(4).io :<>= router.local0Outbound
  receivers(5).io :<>= router.local1Outbound
  receivers(6).io :<>= router.local2Outbound
  receivers(7).io :<>= router.local3Outbound

  val (_, wrapped) = Counter(0 to 131072, true.B, reset.asBool)
  when(wrapped) {
    stop()
  }

  block(VerbosePrint) {
    when(
      router.northInbound.payload.valid && router.northOutbound.payload.ready
    ) {
      val decoderValid = read(router.northDecoderValid)
      val arbiterReady = read(router.northArbiterReady)
      val arbiterGrants = read(router.northArbiterGrants)
      printf(
        cf"[$SimulationTime] Router north status:\n" +
          cf"  Decoder valid: $decoderValid%b\n" +
          cf"  North arbiter ready: $arbiterReady%b\n" +
          cf"  North arbiter grants: $arbiterGrants%b\n"
      )
    }

    when(
      router.southInbound.payload.valid && router.southOutbound.payload.ready
    ) {
      val decoderValid = read(router.southDecoderValid)
      val arbiterReady = read(router.southArbiterReady)
      val arbiterGrants = read(router.southArbiterGrants)
      printf(
        cf"[$SimulationTime] Router south status:\n" +
          cf"  Decoder valid: $decoderValid%b\n" +
          cf"  South arbiter ready: $arbiterReady%b\n" +
          cf"  South arbiter grants: $arbiterGrants%b\n"
      )
    }

    when(
      router.eastInbound.payload.valid && router.eastOutbound.payload.ready
    ) {
      val decoderValid = read(router.eastDecoderValid)
      val arbiterReady = read(router.eastArbiterReady)
      val arbiterGrants = read(router.eastArbiterGrants)
      printf(
        cf"[$SimulationTime] Router east status:\n" +
          cf"  Decoder valid: $decoderValid%b\n" +
          cf"  East arbiter ready: $arbiterReady%b\n" +
          cf"  East arbiter grants: $arbiterGrants%b\n"
      )
    }

    when(
      router.westInbound.payload.valid && router.westOutbound.payload.ready
    ) {
      val decoderValid = read(router.westDecoderValid)
      val arbiterReady = read(router.westArbiterReady)
      val arbiterGrants = read(router.westArbiterGrants)
      printf(
        cf"[$SimulationTime] Router west status:\n" +
          cf"  Decoder valid: $decoderValid%b\n" +
          cf"  West arbiter ready: $arbiterReady%b\n" +
          cf"  West arbiter grants: $arbiterGrants%b\n"
      )
    }

    when(
      router.local0Inbound.payload.valid && router.local0Inbound.payload.ready
    ) {
      val decoderValid = read(router.local0DecoderValid)
      val arbiterReady = read(router.local0ArbiterReady)
      val arbiterGrants = read(router.local0ArbiterGrants)
      printf(
        cf"[$SimulationTime] Router local0 status:\n" +
          cf"  Decoder valid: $decoderValid%b\n" +
          cf"  local0 arbiter ready: $arbiterReady%b\n" +
          cf"  local0 arbiter grants: $arbiterGrants%b\n"
      )
    }

    when(
      router.local1Inbound.payload.valid && router.local1Outbound.payload.ready
    ) {
      val decoderValid = read(router.local1DecoderValid)
      val arbiterReady = read(router.local1ArbiterReady)
      val arbiterGrants = read(router.local1ArbiterGrants)
      printf(
        cf"[$SimulationTime] Router local1 status:\n" +
          cf"  Decoder valid: $decoderValid%b\n" +
          cf"  local1 arbiter ready: $arbiterReady%b\n" +
          cf"  local1 arbiter grants: $arbiterGrants%b\n"
      )
    }

    when(
      router.local2Inbound.payload.valid && router.local2Outbound.payload.ready
    ) {
      val decoderValid = read(router.westDecoderValid)
      val arbiterReady = read(router.westArbiterReady)
      val arbiterGrants = read(router.westArbiterGrants)
      printf(
        cf"[$SimulationTime] Router local2 status:\n" +
          cf"  Decoder valid: $decoderValid%b\n" +
          cf"  local2 arbiter ready: $arbiterReady%b\n" +
          cf"  local2 arbiter grants: $arbiterGrants%b\n"
      )
    }

    when(
      router.local3Inbound.payload.valid && router.local3Outbound.payload.ready
    ) {
      val decoderValid = read(router.westDecoderValid)
      val arbiterReady = read(router.local3ArbiterReady)
      val arbiterGrants = read(router.local3ArbiterGrants)
      printf(
        cf"[$SimulationTime] Router local3 status:\n" +
          cf"  Decoder valid: $decoderValid%b\n" +
          cf"  local3 arbiter ready: $arbiterReady%b\n" +
          cf"  local3 arbiter grants: $arbiterGrants%b\n"
      )
    }
  }
}

class RouterSpec extends AnyFunSpec with ChiselSim {
  val stubParam = NeroParameters(4, 0, 4)

  describe("AXI-S Router") {
    it("should generate verilog") {
      ChiselStage.emitSystemVerilog(new Router(stubParam))
    }

    it("should route signals correctly") {
      val param = NeroParameters(4, 0, 4)
      simulate(new AXISRouterTestHarness(42, param)) {
        RunUntilFinished(131074)
      }
    }
  }
}
