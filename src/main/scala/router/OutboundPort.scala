package nero.router

import chisel3._
import chisel3.util._

import nero.util._
import nero.bundle._

// Rotary mask based round robin.
class RotaryMaskRR(width: Int = 1) extends Module {
  val io = IO(new Bundle {
    val valid = Output(Bool())
    val ready = Input(Bool())
    val input = Input(UInt(width.W))
    val oneHotIndex = Output(UInt(width.W))
  })

  private val mask = RegInit(0.U(width.W))

  private val maskedRequest = mask & io.input
  private val needMaskReset = maskedRequest === 0.U(width.W)

  io.valid := io.input.orR
  io.oneHotIndex := maskedRequest & (~maskedRequest + 1.U(width.W))

  when(io.valid && io.ready) {
    when(needMaskReset) {
      mask := Fill(width, 1.U)
    }.otherwise {
      mask := ~((io.oneHotIndex << 1.U) - 1.U(width.W))
    }
  }
}

class OutboundPort(tileCount: Int, timestampWidth: Int) extends Module {
  val output = IO(Irrevocable(new AXISPayload(tileCount, timestampWidth)))
  val cardinalPorts =
    Seq.fill(4)(
      IO(Flipped(Irrevocable(new AXISPayload(tileCount, timestampWidth))))
    )
  val localPorts = Seq.fill(4)(
    IO(Flipped(Irrevocable(new AXISPayload(tileCount, timestampWidth))))
  )

  private val width = 8
  private val arbiter = Module(new RotaryMaskRR(width))

  private val data = cardinalPorts.map(_.bits) ++ localPorts.map(_.bits)
  private val valids = cardinalPorts.map(_.valid) ++ localPorts.map(_.valid)
  private val allValids = Cat(valids)
  private val readys = cardinalPorts.map(_.ready) ++ localPorts.map(_.ready)

  arbiter.io.ready := output.ready
  arbiter.io.input := allValids

  output.bits := Mux1H(arbiter.io.oneHotIndex.asBools.zip(data).map {
    case (i, data) => i -> data
  })
  output.valid := arbiter.io.valid && allValids.orR
  readys.zip(arbiter.io.oneHotIndex.asBools).foreach { case (ready, mask) =>
    ready := mask
  }
}
