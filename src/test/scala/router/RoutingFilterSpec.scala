package nero.router

import org.scalatest.funspec.AnyFunSpec

import chisel3._
import chisel3.simulator.EphemeralSimulator._

import circt.stage.ChiselStage
import nero.bundle.Coordinate
import nero.parameters.NeroParameters

class RoutingFilterSpec extends AnyFunSpec {
  val stubParam = NeroParameters(4, 0, 4)
  describe("Routing filter") {

    it("should generate verilog") {
      ChiselStage.emitSystemVerilog(new RoutingFilter(stubParam))
    }

    it("should tell forward to west") {
      simulate(new RoutingFilter(stubParam)) { c =>
        // Given that destination is located on (1, 1),
        // this should occur when source's x is greater than
        // destination's.

        c.src.x.poke(2.U(4.W))
        c.src.y.poke(1.U(4.W))
        c.dest.x.poke(1.U(4.W))
        c.dest.y.poke(1.U(4.W))

        c.available.west.expect(true.B)
        c.available.east.expect(false.B)
        c.available.north.expect(false.B)
        c.available.south.expect(false.B)
        c.available.local0.expect(false.B)
        c.available.local1.expect(false.B)
        c.available.local2.expect(false.B)
        c.available.local3.expect(false.B)
      }
    }

    it("should tell forward to east") {
      simulate(new RoutingFilter(stubParam)) { c =>
        // Given that destination is located on (1, 1),
        // this should occur when source's x is lesser than
        // destination's.

        c.src.x.poke(0.U(4.W))
        c.src.y.poke(1.U(4.W))
        c.dest.x.poke(1.U(4.W))
        c.dest.y.poke(1.U(4.W))

        c.available.west.expect(false.B)
        c.available.east.expect(true.B)
        c.available.north.expect(false.B)
        c.available.south.expect(false.B)
        c.available.local0.expect(false.B)
        c.available.local1.expect(false.B)
        c.available.local2.expect(false.B)
        c.available.local3.expect(false.B)
      }
    }

    it("should tell forward to north") {
      simulate(new RoutingFilter(stubParam)) { c =>
        // Given that destination is located on (1, 1),
        // this should occur when source's y is lesser than
        // destination's.

        c.src.x.poke(1.U(4.W))
        c.src.y.poke(0.U(4.W))
        c.dest.x.poke(1.U(4.W))
        c.dest.y.poke(1.U(4.W))

        c.available.west.expect(false.B)
        c.available.east.expect(false.B)
        c.available.north.expect(true.B)
        c.available.south.expect(false.B)
        c.available.local0.expect(false.B)
        c.available.local1.expect(false.B)
        c.available.local2.expect(false.B)
        c.available.local3.expect(false.B)
      }
    }

    it("should tell forward to south") {
      simulate(new RoutingFilter(stubParam)) { c =>
        // Given that destination is located on (1, 1),
        // this should occur when source's y is greater than
        // destination's.

        c.src.x.poke(1.U(4.W))
        c.src.y.poke(2.U(4.W))
        c.dest.x.poke(1.U(4.W))
        c.dest.y.poke(1.U(4.W))

        c.available.west.expect(false.B)
        c.available.east.expect(false.B)
        c.available.north.expect(false.B)
        c.available.south.expect(true.B)
        c.available.local0.expect(false.B)
        c.available.local1.expect(false.B)
        c.available.local2.expect(false.B)
        c.available.local3.expect(false.B)
      }
    }

    it("should tell forward to first local") {
      simulate(new RoutingFilter(stubParam)) { c =>

        c.src.x.poke(1.U(4.W))
        c.src.y.poke(1.U(4.W))
        c.dest.x.poke(1.U(4.W))
        c.dest.y.poke(1.U(4.W))
        c.local.x.poke(0.U)
        c.local.y.poke(0.U)

        c.available.west.expect(false.B)
        c.available.east.expect(false.B)
        c.available.north.expect(false.B)
        c.available.south.expect(false.B)
        c.available.local0.expect(true.B)
        c.available.local1.expect(false.B)
        c.available.local2.expect(false.B)
        c.available.local3.expect(false.B)
      }
    }

    it("should tell forward to second local") {
      simulate(new RoutingFilter(stubParam)) { c =>

        c.src.x.poke(1.U(4.W))
        c.src.y.poke(1.U(4.W))
        c.dest.x.poke(1.U(4.W))
        c.dest.y.poke(1.U(4.W))
        c.local.x.poke(1.U)
        c.local.y.poke(0.U)

        c.available.west.expect(false.B)
        c.available.east.expect(false.B)
        c.available.north.expect(false.B)
        c.available.south.expect(false.B)
        c.available.local0.expect(false.B)
        c.available.local1.expect(true.B)
        c.available.local2.expect(false.B)
        c.available.local3.expect(false.B)
      }
    }

    it("should tell forward to third local") {
      simulate(new RoutingFilter(stubParam)) { c =>

        c.src.x.poke(1.U(4.W))
        c.src.y.poke(1.U(4.W))
        c.dest.x.poke(1.U(4.W))
        c.dest.y.poke(1.U(4.W))
        c.local.x.poke(0.U)
        c.local.y.poke(1.U)

        c.available.west.expect(false.B)
        c.available.east.expect(false.B)
        c.available.north.expect(false.B)
        c.available.south.expect(false.B)
        c.available.local0.expect(false.B)
        c.available.local1.expect(false.B)
        c.available.local2.expect(true.B)
        c.available.local3.expect(false.B)
      }
    }

    it("should tell forward to fourth local") {
      simulate(new RoutingFilter(stubParam)) { c =>

        c.src.x.poke(1.U(4.W))
        c.src.y.poke(1.U(4.W))
        c.dest.x.poke(1.U(4.W))
        c.dest.y.poke(1.U(4.W))
        c.local.x.poke(1.U)
        c.local.y.poke(1.U)

        c.available.west.expect(false.B)
        c.available.east.expect(false.B)
        c.available.north.expect(false.B)
        c.available.south.expect(false.B)
        c.available.local0.expect(false.B)
        c.available.local1.expect(false.B)
        c.available.local2.expect(false.B)
        c.available.local3.expect(true.B)
      }
    }

    it("should tell forward to northwest") {
      simulate(new RoutingFilter(stubParam)) { c =>

        c.src.x.poke(2.U(4.W))
        c.src.y.poke(0.U(4.W))
        c.dest.x.poke(1.U(4.W))
        c.dest.y.poke(1.U(4.W))
        c.local.x.poke(1.U)
        c.local.y.poke(1.U)

        c.available.west.expect(true.B)
        c.available.east.expect(false.B)
        c.available.north.expect(true.B)
        c.available.south.expect(false.B)
        c.available.local0.expect(false.B)
        c.available.local1.expect(false.B)
        c.available.local2.expect(false.B)
        c.available.local3.expect(false.B)
      }
    }

    it("should tell forward to northeast") {
      simulate(new RoutingFilter(stubParam)) { c =>

        c.src.x.poke(0.U(4.W))
        c.src.y.poke(0.U(4.W))
        c.dest.x.poke(1.U(4.W))
        c.dest.y.poke(1.U(4.W))
        c.local.x.poke(1.U)
        c.local.y.poke(1.U)

        c.available.west.expect(false.B)
        c.available.east.expect(true.B)
        c.available.north.expect(true.B)
        c.available.south.expect(false.B)
        c.available.local0.expect(false.B)
        c.available.local1.expect(false.B)
        c.available.local2.expect(false.B)
        c.available.local3.expect(false.B)
      }
    }

    it("should tell forward to southwest") {
      simulate(new RoutingFilter(stubParam)) { c =>

        c.src.x.poke(2.U(4.W))
        c.src.y.poke(2.U(4.W))
        c.dest.x.poke(1.U(4.W))
        c.dest.y.poke(1.U(4.W))
        c.local.x.poke(1.U)
        c.local.y.poke(1.U)

        c.available.west.expect(true.B)
        c.available.east.expect(false.B)
        c.available.north.expect(false.B)
        c.available.south.expect(true.B)
        c.available.local0.expect(false.B)
        c.available.local1.expect(false.B)
        c.available.local2.expect(false.B)
        c.available.local3.expect(false.B)
      }
    }

    it("should tell forward to southeast") {
      simulate(new RoutingFilter(stubParam)) { c =>

        c.src.x.poke(0.U(4.W))
        c.src.y.poke(2.U(4.W))
        c.dest.x.poke(1.U(4.W))
        c.dest.y.poke(1.U(4.W))
        c.local.x.poke(1.U)
        c.local.y.poke(1.U)

        c.available.west.expect(false.B)
        c.available.east.expect(true.B)
        c.available.north.expect(false.B)
        c.available.south.expect(true.B)
        c.available.local0.expect(false.B)
        c.available.local1.expect(false.B)
        c.available.local2.expect(false.B)
        c.available.local3.expect(false.B)
      }
    }
  }
}
