package nero.router

import chisel3._
import chisel3.util.PriorityEncoderOH
import chisel3.util.PopCount

import nero.util.PriorityEncoder

class RoundRobinArbiter(width: Int) extends Module {
  val io = IO(new Bundle {
    val req = Input(UInt(width.W))
    val ack = Input(Bool())
    val grant = Output(UInt(width.W)) // Should be onehot-0, at most one bit is 1.
  })

  // Updating grant
  val mask = RegInit(0.U(width.W))
  val maskedReq = io.req & mask
  val hasRequest = maskedReq.orR

  val selected = Mux(hasRequest, maskedReq, io.req)
  io.grant := PriorityEncoderOH(selected)

  // Updating mask
  when (io.ack) {
    mask := ~((io.grant << 1.U) - 1.U)
  }

  assert(PopCount(io.grant) <= 1.U, "Arbiter granted more than 1 target at a time")
}
