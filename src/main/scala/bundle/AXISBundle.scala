package nero.bundle

import chisel3._
import chisel3.util._
import chisel3.experimental.dataview.DataView

import nero.parameters.NeroParameters

class AXISPayload(tileCount: Int, timestampWidth: Int) extends Bundle {
  val TSRC = UInt((2 * log2Ceil(tileCount + 1)).W)
  val TDEST = UInt((2 * log2Ceil(tileCount + 1)).W)

  // {src_type, packet_type, ctrl_inst[3:0], timestamp}
  val TDATA = UInt((timestampWidth + 6).W)
}

class VerilogAXISBundle(val param: NeroParameters) extends Bundle {
  val TVALID = Output(Bool())
  val TREADY = Input(Bool())
  val TID = Output(UInt((2 * log2Ceil(param.tileCount + 1)).W))
  val TDEST = Output(UInt((2 * log2Ceil(param.tileCount + 1)).W))
  val TDATA = Output(UInt(param.timestampWidth.W))
}

class AXISBundle(param: NeroParameters) extends Bundle {
  val payload = Irrevocable(new NeroPayload(param))
}

object AXISBundle {
  implicit val axisView: DataView[VerilogAXISBundle, AXISBundle] = DataView(
      vab => new AXISBundle(vab.param),
      _.TVALID -> _.payload.valid,
      _.TREADY -> _.payload.ready,
      _.TID -> _.payload.bits.src,
      _.TDEST -> _.payload.bits.dest,
      _.TDATA -> _.payload.bits.timestamp
    )
}

class NeroPayload(param: NeroParameters) extends Bundle {
  val src = Wire(new Coordinate(param.tileCount))
  val dest = Wire(new Coordinate(param.tileCount))
  val local = Wire(new Coordinate(1))
  val timestamp = UInt(param.timestampWidth.W)
}

class Coordinate(tileCount: Int) extends Bundle {
  private val wireWidth = tileCount.max(1)
  val x = UInt(log2Ceil(wireWidth).W)
  val y = UInt(log2Ceil(wireWidth).W)
}
