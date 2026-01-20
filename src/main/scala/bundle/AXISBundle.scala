package nero.bundle

import chisel3._
import chisel3.util._

// Only implements a subset of optional AXIS fields.
class AXISBundle(tileCount: Int, timestampWidth: Int) extends Bundle {
  val TVALID = Bool()
  val TREADY = Flipped(Bool())
  val TSRC = UInt((2 * log2Ceil(tileCount + 1)).W)
  val TDEST = UInt((2 * log2Ceil(tileCount + 1)).W)

  // {src_type, packet_type, ctrl_inst[3:0], timestamp}
  val TDATA = UInt((timestampWidth + 6).W)
}

class AXISPayload(tileCount: Int, timestampWidth: Int) extends Bundle {
  val TSRC = UInt((2 * log2Ceil(tileCount + 1)).W)
  val TDEST = UInt((2 * log2Ceil(tileCount + 1)).W)

  // {src_type, packet_type, ctrl_inst[3:0], timestamp}
  val TDATA = UInt((timestampWidth + 6).W)
}
