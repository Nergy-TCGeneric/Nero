package nero.parameters

case class NeroParameters(
  val tileCount: Int,
  val timestampWidth: Int,
  val localTilesPerRouter: Int
)
