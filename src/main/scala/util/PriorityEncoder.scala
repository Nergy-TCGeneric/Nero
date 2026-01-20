package nero.util

import chisel3._

class PriorityEncoder(width: Int = 1) extends Module
{
  val io = IO(new Bundle {
    val input = Input(UInt(width.W))
    val index = Output(UInt(width.W))
    val valid = Output(Bool())
  })

  io.index := chisel3.util.PriorityEncoder(io.input)
  io.valid := io.input.orR
}
