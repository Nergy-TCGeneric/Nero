package nero.router

import org.scalatest.funspec.AnyFunSpec

import circt.stage.ChiselStage

import chisel3._
import chisel3.util.random.MaxPeriodGaloisLFSR
import chisel3.util._
import chisel3.simulator.scalatest.ChiselSim
import chisel3.simulator.stimulus.RunUntilFinished
import chisel3.simulator.HasSimulator

import nero.parameters.NeroParameters
import nero.bundle.AXISBundle
import nero.util._

private class AXISPacketFuzzer(seed: Int, param: NeroParameters)
    extends Module {
  val io = IO(new AXISBundle(param))

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
