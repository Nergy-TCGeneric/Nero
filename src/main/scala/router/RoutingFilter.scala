package nero.router

import chisel3._
import chisel3.util._

import nero.bundle.Coordinate
import nero.parameters.NeroParameters

class RoutingFilter(param: NeroParameters) extends Module {
  require (param.localTilesPerRouter == 4, "Routing filter currently only accepts localTilesPerRouter = 4")

  val src = IO(Input(new Coordinate(param.tileCount)))
  val dest = IO(Input(new Coordinate(param.tileCount)))
  val local = IO(Input(new Coordinate(log2Ceil(param.localTilesPerRouter))))

  val available = IO(new Bundle {
    val north = Output(Bool())
    val east = Output(Bool())
    val west = Output(Bool())
    val south = Output(Bool())
    val local0 = Output(Bool())
    val local1 = Output(Bool())
    val local2 = Output(Bool())
    val local3 = Output(Bool())
  })

  // Cardinal port
  val isWestBound = dest.x < src.x
  val isSouthBound = dest.y < src.y

  val isXLocalBound = dest.x === src.x
  val isYLocalBound = dest.y === src.y
  val isLocalBound = isXLocalBound && isYLocalBound

  // Local port, x first
  val localCoord = Cat(local.y, local.x)
  val localMuxed = UIntToOH(localCoord, 4)
  val localSelection = localMuxed & Fill(4, isLocalBound)

  available.north := !isSouthBound && !isYLocalBound
  available.east := !isWestBound && !isXLocalBound
  available.west := isWestBound && !isXLocalBound
  available.south := isSouthBound && !isYLocalBound

  available.local0 := localSelection(0)
  available.local1 := localSelection(1)
  available.local2 := localSelection(2)
  available.local3 := localSelection(3)

  private val cardinalOutput = Cat(
    available.north, available.east, available.west, available.south
  )
  private val localOutput = Cat(
    available.local0, available.local1, available.local2, available.local3
  )
  private val output = Cat(cardinalOutput, localOutput)

  assert(PopCount(output) =/= 0.U, "Output should be non-zero for all times")
  assert(cardinalOutput.orR ^ localOutput.orR === true.B, "Cardinal and local output must be mutually exclusive")
  assert(PopCount(localOutput) <= 1.U, "At most one local output can be asserted at a time")
}
