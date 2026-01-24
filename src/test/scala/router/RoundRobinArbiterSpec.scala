package nero.router

import org.scalatest.funspec.AnyFunSpec

import chisel3._
import chisel3.simulator.EphemeralSimulator._
import circt.stage.ChiselStage

class RoundRobinArbiterSpec extends AnyFunSpec {
  describe("Round robin arbiter") {
    it("should grant request from lowest bit to highest") {
      // All requests are remained HIGH, to see if arbiter
      // grants each request for every N-1 cycles.
      simulate(new RoundRobinArbiter(4)) { c =>
        // initialization
        c.reset.poke(true.B)
        c.clock.step()
        c.reset.poke(false.B)
        c.clock.step()

        c.io.ack.poke(true.B)
        c.io.req.poke(15.U)

        c.io.grant.expect(1.U(4.W))
        c.clock.step()
        c.io.grant.expect(2.U(4.W))
        c.clock.step()
        c.io.grant.expect(4.U(4.W))
        c.clock.step()
        c.io.grant.expect(8.U(4.W))
        c.clock.step()
        c.io.grant.expect(1.U(4.W))
      }
    }

    it("should grant no one if all requests are low") {
      simulate(new RoundRobinArbiter(4)) { c  =>
        // No initialization necessary.

        c.io.ack.poke(true.B)
        c.io.req.poke(0.U(4.W))
        c.io.grant.expect(0.U(4.W))

        // Grant must remain 0, if there's no further request
        c.clock.step()
        c.io.grant.expect(0.U(4.W))
      }
    }
  }
}
