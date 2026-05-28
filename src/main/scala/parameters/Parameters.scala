package nero.parameters

import chisel3.util.log2Ceil

case class NeroParameters(
    val tileCount: Int,
    val timestampWidth: Int,
    val localTilesPerRouter: Int
) {
  // src/dest xy width + local tile width
  def totalWireWidth = 4 * log2Ceil(tileCount) + 2
}
