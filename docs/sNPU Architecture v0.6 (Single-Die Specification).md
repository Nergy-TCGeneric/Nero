---
created: 2025-10-19 18:50
modified: 2026-05-17 13:16
---
Previous work:
- [[SNN NoC Fabric]]
- [[Spikeability Checker]]

Related:
- [[sNPU Architecture Roadmap v0.2]]

Last updated: 26-01-26 22:16

# Revision Log

| Date       | Version | Change Log                                                                  |
| ---------- | ------- | --------------------------------------------------------------------------- |
| 2025-10-20 | v0      | Initial Draft                                                               |
| 2025-10-22 | v0.1    | Specialized to 'Single-Die Specification'                                   |
| 2025-10-25 | v0.2    | Modularized neuron tile composition                                         |
| 2025-12-19 | v0.3    | Added tile coordinate constraint                                            |
| 2026-01-21 | v0.4    | Changed `NEURON_TILE_COUNT` to `ROUTER_COUNT`                               |
| 2026-01-26 | v0.5    | - Added event and response format<br>- Removed spike replication capability |
| 2026-05-17 | v0.6    | - Added 'stall' flag note                                                   |

# 1. Executive Summary

> [[sNPU Nero|sNPU "Nero"]] is a scalable, modular and tile-based [[Spiking Neural Network (SNN)]] accelerator.

A single die hosts N by N inner tiles arranged in 2D mesh, surrounded by a small number of outer tiles that provide off-chip interface (UART, SPI, PCIe, etc.).
All intra-die communication uses a [[Network-on-Chip (NoC)]] that routes packets via routers to neuron tiles.

The design intentionally keeps many parameters (e.g., neuron counts, weight widths) parameterized so that the same spec drives both FPGA and ASIC implementations.

# 2. Glossary

| Term              | Definition                                                                                                                      |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Outer tile        | Tile that exposes the off-chip interface. Mainly communicates with host, but optionally with other sNPU chips.                  |
| Inner tile        | Tiles that cannot be accessed from outside directly. Refers a group consists of router and its one or more neuron tiles.        |
| Router (Synapse)  | Core of an inner tile. Implements a spike-routing table and forwards spike to cardinal neighbors or to associated neuron tiles. |
| Neuron tile       | Implements a single spiking neuron based on [[Leaky Integrate and Fire\|LIF]] with learning and neuromodulation support.        |
| Grid coordinate   | 2D integer pair `(x, y)` identifying a tile's position in the mesh.                                                             |
| Packet            | A payload sent over the NoC.                                                                                                    |
| Eligibility trace | A register that records the timing of pre/post-spike events for STDP updates.                                                   |
| Dopamine buffer   | Per-neuron register that decays over time and gates DA-STDP learning.                                                           |

# 3. High-Level Architecture

**Functional Diagram**

```
           +------------+  Host IF +-------------+
           | Outer tile |<-------->|    Host     |
           +--+---------+          +-------------+
              |       ^                           
Inner tile's  |       |                           
protocol      |       |                           
              |       |                           
              v       |                           
           +----------+-+          +-------------+
           | Inner tile |<--....-->| Inner tiles |
           +------------+          +-------------+
                       NoC Connection             
                         (2-D Mesh)               
```

- The mesh is N by N. Each inner tile is linked to its four cardinal neighbors (N, S, E, W).
- Outer tiles are fixed in number (typically 1 or 4) and occupy the periphery. They are the *only* tiles that have an off-chip interface.
- All spike packets travel in *unidirectional bursts* with a simple read/valid handshake along the cardinal links. A router can generate back-pressure to upstream tiles.

**Placement**

```
+-----------------------------------+                              
|     +----------------------+      |                              
|     |     Outer tiles      |      |                              
|     +----------------------+      |                              
| +-+ +---++---++---+     +---+ +-+ |                              
| | | |   ||   ||   |     |   | | | |                              
| | | |   ||   ||   | ... |   | | | |                              
| | | |   ||   ||   |     |   | | | |                              
| | | +---++---++---+     +---+ | | |                              
| |O| +---++---++---+     +---+ |O| |                              
| |u| |   ||   ||   |     |   | |u| |                              
| |t| |   ||   ||   | ... |   | |t| |  UART/SPI/PCIe...  +--------+
| |e| |   ||   ||   |     |   | |e| | via Host interface |        |
| |r| +---++---++---+     +---+ |r| |                    |        |
| | | +---++---++---+     +---+ | | | <----------------> |  Host  |
| |t| |   ||   ||   |     |   | |t| |                    |        |
| |i| |   ||   ||   | ... |   | |i| |                    |        |
| |l| |   ||   ||   |     |   | |l| |                    +--------+
| |e| +---++---++---+     +---+ |e| |                              
| |s|   .    .    .   .         |s| |                              
| | |   .    .    .    .        | | |                              
| | |   .    .    .     .       | | |                              
| | | +---++---++---+     +---+ | | |                              
| | | |   ||   ||   |     |   | | | |                              
| | | |   ||   ||   |     |   | | | |                              
| | | |   ||   ||   |     |   | | | |                              
| +-+ +---++---++---+     +---+ +-+ |                              
|     +-----------------------+     |                              
|     |      Outer tiles      |     |                              
|     +-----------------------+     |                              
+-----------------------------------+                              
                                                                   
              sNPU Nero                                              
```

# 4. Design parameters

| Name                    | Recommended value    | Role                                    |
| ----------------------- | -------------------- | --------------------------------------- |
| `ROUTER_COUNT`          | 2 ~ 128              | The 'N' in the N by N mesh. Max 128.    |
| `WEIGHT_WIDTH`          | 8/16                 | Synaptic weight width in bits           |
| `DOPAMINE_BUFFER_WIDTH` | 8/16                 | Dopamine buffer width in bits           |
| `E_TRACE_WIDTH`         | 4/8                  | Eligibility trace width in bits         |
| `R_PERIOD_WIDTH`        | 4/8                  | Refractory period width in bits         |
| `COEFFICIENT_WIDTH`     | = `WEIGHT_WIDTH`     | Weight delta coefficient width in bits  |
| `TIMESTAMP_WIDTH`       | 16                   | Timestamp width in bits                 |
| `MAX_CONNECTION`        | `ROUTER_COUNT`^2 / 2 | Maximum fanout connection count         |
| `NEURONS_PER_ROUTER`    | 1 ~                  | Associated neuron tile count per router |

# 5. Outer tiles considerations

If outer tiles need to communicate with inner tiles, they must support protocol that used on internal tiles. One example is an ingress and egress tile which injects inbound packet and aggregates outbound packets respectively.

## 5.1. Outer tile coordinates

Every outer tiles must have following cartesian coordinate $(x, y)$ under the following rule,
$$ x \in \{0, L+1\} \; \lor \; y \in \{0, L+1\} $$
where $L$ is `ROUTER_COUNT`. Simply put, every outer tiles must reside on the 'edge'. For example, the followings can be a valid outer coordinates assuming $L$ is 2.

- (0, 0)
- (0, 3)
- (1, 3)
- (3, 1)
- (3, 3)

# 6. Inner tile composition

As stated on glossary, inner tiles are not directly visible to off-chip components.

## 6.1. Inner tile coordinates

Every inner tiles must have following cartesian coordinate $(x, y)$ under the following rule,
$$ 0 < x < (L+1) \; \land \; 0 < y < (L+1) $$

where $L$ is `ROUTER_COUNT`. For example, the followings can be a valid outer coordinates assuming $L$ is 2.

- (1, 1),
- (1, 2),
- (2, 1),
- (2, 2)
## 6.2 Neuron tile

Each neuron tile represents a single spiking neuron.

Neurons only communicate with these inbound and outbound packets. That is, neurons should only have packet interface but nothing else.

### 6.2.1 Packet Format

Regardless of packet protocol, following fields are mandatory:

| Field       | Width                      | Description                                                              |
| ----------- | -------------------------- | ------------------------------------------------------------------------ |
| `src_x`     | `ceil(log2(ROUTER_COUNT))` | Source node's `x` coord<br>                                              |
| `src_y`     | `ceil(log2(ROUTER_COUNT))` | Source node's `y` coord                                                  |
| `dest_x`    | `ceil(log2(ROUTER_COUNT))` | Destination node's `x` coord                                             |
| `dest_y`    | `ceil(log2(ROUTER_COUNT))` | Destination node's `y` coord                                             |
| `timestamp` | `TIMESTAMP_WIDTH`          | Packet creation timestamp                                                |
| `payload`   | 16                         | Payload for response/event                                               |
| `header`    | 8                          | Packet header information. Refer 7. Event and Response for more details. |


It doesn't necessarily have to ship these fields as is. If some protocol can cover these semantically, like combining `src_x` and `src_y` as a `TID` in AXIS, it doesn't matter.

It's then up to implementation details what to append after these mandatory fields. These are considered 'optional' and one possible example could be interface signals like:

| Field    | Width | Description                   |
| -------- | ----- | ----------------------------- |
| `TLAST`  | 1     | Last packet indicator in AXIS |
| `TVALID` | 1     | AXIS Valid signal             |
| `TREADY` | 1     | AXIS Ready signal             |
| ...      |       |                               |
### 6.2.2 Modularized neuron architecture

A neuron tile is designed to be modular, i.e, developers can decide which 'feature' they want to include into their design or not. Each feature comes with their unique code to distinguish themselves from others.

A mandatory feature is marked as (mandatory). Every Nero-based design must implement these to be spec-compliant. Options are marked as (optional). Developers can simply opt-out if these do not meet their requirements.

Following RISC-V ISA's convention, developers may denote which feature is implemented in their design by appending a code. For example, 'Potential updates' feature has code name P. If a design only implements such feature, developers can attach a code like following,

> Nero-P

If multiple features were implemented, for example 'Refractory period' as well then:

> Nero-PR

It's advised to append code in order they're listed in specification. 'Potential updates' come first before 'Refractory period', so as shown above it should be 'PR' but not 'RP'.

### 6.2.3 Potential updates (Mandatory, P)

A spiking neuron is a stateful element, which has a time-varing value called membrane potential $V_{mem}$. Given a threshold $V_t$, whenever $V_{mem} \geq V_t$ it fires an outbound packet.

$V_{mem}$ update occurs every clock cycle and follows the [[Leaky Integrate and Fire]], as presented as following ODE. Leak term is applied by a constant coefficient $\tau_{l}$:

$$ \frac{dV_{mem}}{dt} = -\frac{1}{\tau_{l}} [V_{mem}(t) + RI(t)]$$
Where,

- $V_{mem}(t)$ is a membrane potential varying by time $t$
- $I(t)$ is an input current at time $t$ (likely a pulse input)

After emitting a spike packet, $V_{mem}$ is reset to 0. If refractory period exists, refer 6.2.4. Refractory period for more details.

A neuron must maintain a 'weight table' to correctly update $V_{mem}$ from various sources. Whenever a neuron receives a spike, corresponding weight $w$ updates $V_{mem}$. By any circumstance, the 'signess' on each weight $w$ must be preserved. 
For example, a negative weight $w$ -0.3 must stay negative for a whole time even if its magnitude changes by learning algorithm.

It's an error to receive a spike from a source not registered on such weight table.

### 6.2.4 Refractory period (Optional, R)

After firing a spike, for given a refractory period $T_L$ clock(s) neuron cannot fire a subsequent spikes. $T_L$ is a positive integer which is $T_L \geq 0$.

Two options are possible how $V_{mem}$ should be updated when received a spike during a refractory until it ends:

1. Let no $V_{mem}$ update happen,
2. Or update $V_{mem}$ as usual but do not fire a spike even if it exceeds $V_t$

It's up to implementation what to choose between both.

### 6.2.5 Learning modes (Optional, L)

A neuron tile should support three types of learning method:

1. Frozen (No weight change will ever happen)
2. STDP
3. *DA-STDP (Optional)*

It's an error to set a learning mode not defined in this specification. If this feature is not going to be implemented, it's advised to let weight stay frozen.

Whenever it received or fired a spike, it first initializes the Eligibility trace buffer, $e(t)$ with maximum value. This buffer decays over time exponentially following the below ODE, assuming no external input is present:
$$ \frac{de(t)}{dt} = -\frac{e(t)}{\tau} $$
A recommended decay constant value is $\tau$ = 100 (cycles).

It's then who fired the spike that decreases the weight (LTD) or increases the weight (LTP). 

Weight delta is calculated as follows, as vanilla STDP does:
$$ \delta W = A_{pre} \times G(t) \times e{(t_{post} - t_{pre})} \ (\text{LTP})$$
$$ \delta W = A_{post} \times G(t) \times e(t_{pre} - t_{post}) \ (\text{LTD})$$
where:

- $t$ is a current timestamp
- $G(t)$ is a boolean learning gating function
- $t_{pre}$ is a time when pre-synaptic spike occured
- $t_{post}$ is a time when post-synaptic spike occured
- $A_{pre}$ and $A_{post}$ are weight update coefficient
- $\text{e}$ is a Eligibility trace buffer decays by $t_{pre} - t_{post}$ respectively.

And $G(t)$ is dependent to learning mode:

- For Frozen, $G(t) = 0$ for all time. 
- For STDP, $G(t) = 1$ for all time. 
- For DA-STDP, the value of $G(t)$ is determined by Dopamine buffer.

If expressed in pseudocode:

==TODO: Pseudocode is not right; revise this later==

```
# Global parameter: A_pre, A_post, w_max
# Per synapse: e (Eligiblity trace buffer), w (Weight)

# on each dt:
e *= exp(-dt/tau)

if pre_spike:
	e += A_pre
	w = clip(w + Apost * e, 0, w_max)
if post_spike:
	e += A_post
	w = clip(w + A_pre * e, 0, w_max)
```

### 6.2.6 Dopaminergic neuromodulation (Optional, D)

From another neuron or external intervention, a neuron may receive a dopaminergic neuromodulator.

Once received, it initializes the dopamine buffer to maximum value. Buffer should decay continuously over time to zero, preferably linearly.

How fast such dopamine buffer should decay and should affect to DA-STDP learning method is up to implementation details. One possible implementation is letting dopamine buffer decay within 1,000 clocks upon initialization to zero and let $G(t) = 1$ until buffer hits 0.

### 6.2.7. Trace logging (Optional, T)

Any time a neuron tile receives a packet from other tile or a host, it should store following events:

1. When this was received
2. Who sent this

Optionally, it's up to implementation what to store more. One recommendation is neuron's membrane potential $V_{mem}$ at that moment as it can boost up runtime reconstruction on host side.

Whenever the existing log was overwritten, like an overflow occured it should flag itself so that host can know there are some missing logs on further inspection.

### 6.2.8. Dynamic connection (Optional, C)

When requested from host, a neuron must establish a connection,

1. With a tile corresponds with a supplied destination
2. With a weight $w$

This connection can be configured dynamically, but it's advised to do so when there's no incoming spike packets.

### 6.2.9 Implementation recommendations

To fulfill every requirements above, you may consider implementing these:

| Register                     | Width (bit)             | Role                                                                                                                |
| ---------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Membrane potential           | `WEIGHT_WIDTH`          | Stores instantaneous membrane voltage                                                                               |
| Threshold                    | `WEIGHT_WIDTH`          | Stores spike firing threshold                                                                                       |
| Learning mode                | 2                       | Stores learning mode,<br>- 2'b00 : Frozen<br>- 2'b01 : STDP<br>- 2'b10 : *DA-STDP (Optional)*<br>- 2'b11 : Reserved |
| Learning gate                | 1                       | Determines whether weight change should happen. Disabled if 0, enabled if 1.                                        |
| Eligibility trace            | `E_TRACE_WIDTH`         | Stores weight change upon pre-/post-spike event. Decays over time (implementation-dependent).                       |
| Refractory period length     | `R_PERIOD_WIDTH`        | Stores refractory period length.                                                                                    |
| LTD weight coefficient       | `COEFFICIENT_WIDTH`     | Stores coefficient for calculating weight change on Long Term Depression (LTD).                                     |
| LTP weight coefficient       | `COEFFICIENT_WIDTH`     | Stores coefficient for calculating weight change on Long Term Potentiation (LTP).                                   |
| *Dopamine buffer (Optional)* | `DOPAMINE_BUFFER_WIDTH` | Gated DA-STDP Buffer, decays over time (implementation-dependent).                                                  |
| Local timer                  | `TIMESTAMP_WIDTH`       | Timer for recording packet timestamp.                                                                               |
| Last spike timer             | `TIMESTAMP_WIDTH`       | Stores 'last spiked time' as a timestamp.                                                                           |

| Memory                | Width (bit)                        | Role                                        |
| --------------------- | ---------------------------------- | ------------------------------------------- |
| Synaptic weight table | `WEIGHT_WIDTH` \* `MAX_CONNECTION` | Synaptic weight from each possible sources. |

## 6.3 Router

A router represents a 'synapse'. It forward spikes toward the destination. Such router exposes five bi-directional ports as presented in table:

| Port | Direction              | Purpose                                                    |
| ---- | ---------------------- | ---------------------------------------------------------- |
| N    | North                  | Connects to the router whose grid coordinate is $(x, y+1)$ |
| E    | East                   | Connects to the router whose grid coordinate is $(x+1,y)$  |
| W    | West                   | Connects to the router whose grid coordinate is $(x-1,y)$  |
| S    | South                  | Connects to the router whose grid coordinate is $(x,y-1)$  |
| T    | Local (to/from neuron) | Interface to associated neuron tile (neuron-router link)   |

**Visualized port**

```
             (x,y+1)                
                N                   
          +------------+            
          |            |            
          |            |            
          |            |            
(x-1,y) W |   Router   | E (x+1,y)  
          |            |            
          |            |            
          |            |            
          +------------+            
                S      ^ T (Local)       
             (x,y-1)   |            
                       +-->+---+    
                           |   |    
                           |   |    
                           |   |    
                           +---+    
                         Neuron tile
```

### 6.3.1 Spike routing scheme

When a router received a spike, it should forward spike to one of available ports. An outbound port is 'available' if the downstream routers are not stalled, mostly when their FIFO is not full. A router shall stall inbound spike traffic if no available output port exists.

Every router must maintain a 'routing table' that maps an incoming spike to the next-hop direction. Such routing table must be either: 

1. Forward spike to any of cardinal direction port
2. Or to local port only. 

It's an error to allow both cases at once.

When choosing a port, following rules apply:

1. Only choose ports that forwards incoming packet toward its destination.
2. If it's set to cardinal direction, pick a port by following order: East > West > North  > South. East port has the highest priority and South port has the lowest priority. If it's local, then only a local port is selected.
3. If first candidate from 2. is unavailable right now, select the next available one.
4. If none of the ports are available, wait until the neighbor flags itself as 'ready'.

**Example**
Given a spike coming from $(3, 4)$ and routing table says 'North' and 'South', a router should redirect spike to north port. However if such port is unavailable because a neighbor is busy, then it chooses the next, south port. If none of them are available, router waits until one of ports become available again.

When forwarding a spike, it can be queued or stalled but it **MUST NOT** be dropped under any circumstances. A FIFO *may* be placed on the inbound path of each port to buffer bursts of spikes that arrive while a downstream port is stalled and one may employ 'stalled' flag so any downstream application can know this neuron once had been stalled before by spike traffic.

It's an error to receive spike from neuron whose grid location is not registered on routing table.

### 6.3.2 Delay considerations

Except an autapse (a neuron is connected to itself), it's worth note that neuron to neuron spikes take some cycles to arrive.

This is up to implementation, but normally it's expected that a baseline latency, a minimum required clock to arrive a destination, $L$ is calculated as: $$L = 2 + D_H $$ $D_H$ is a number of router hops between the source and the destination, which is the number of router boundaries crossed. The constant 2 accounts for round-trip latency: one clock for source tile -> router forwarding and another for router -> destination tile.

It's worth knowing that in practice, back-pressure or buffering may add extra cycles, but the system must still guarantee that the spike eventually reaches its destination.

### 6.3.3 Arbitrating multiple outbound spikes

If more than a single spike have to go out through a port at the same time, a router must decide which spike should be forwarded first until there are no pending spikes remaining.

The arbitration scheme is implementation-dependent, but such implementation must guarantee that no deadlock would occur. Also, dropping a spike on arbitration is **strictly forbidden.** It's recommended to use deterministic and bounded method like round-robin for predictable results.

### 6.3.4 Multiple neuron tiles (Optional, M)

A router may have more than a single neuron tile. To distinguish a destination among associated neurons, the spike packet must carry following field:

| Field            | Width                                 | Description           |
| ---------------- | ------------------------------------- | --------------------- |
| `src_neuron_id`  | `ceil(log2(NEURON_TILES_PER_ROUTER))` | Source neuron id      |
| `dest_neuron_id` | `ceil(log2(NEURON_TILES_PER_ROUTER))` | Destination neuron id |

As routers have to forward spikes to corresponding destination, addition to 6.2.1 Spike routing scheme:

1. If `dest_x` and `dest_y` is equal to router's `x` and `y`,
		a. For each local port, send spike to port that `dest_neuron_id` == `id`.
2. Otherwise, follow 6.2.1's Spike routing scheme.

It's an error to receive a spike which contains `dest_neuron_id` that does not exist on router. For example, it's invalid to receive a spike with `dest_neuron_id` = 3 when there's only two neurons associated with a router.

# 7. Event and Response

Each packet falls into one of category: 'Event' and 'Response'. Any tiles can issue an event to other and it's guaranteed to eventually arrive at destination. Optionally, some event requires recipient to send a response.

Both can be multi-flit. This means they may be consisted of more than a single packet. Any event and response that originated from identical source and heading the same destination must arrive in order.

Both event and response are 24-bits format.

## 7.1. Response

![[Response Packet Bit field.png]]

| Bit index | Name          | Description                                                                                                                                    |
| --------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 23:8      | Payload       | Field for some responses which carries value.                                                                                                  |
| 7:4       | Reserved      | *Reserved*                                                                                                                                     |
| 3:2       | Response code | A recipient response.<br>- `2'b00`: OKAY<br>- `2'b01` : RECERR (Recipient Err.)<br>- `2'b10` : DECERR (Decoder Err.)<br>- `2'b11` : *Reserved* |
| 1         | Payload Valid | Payload is valid when asserted. Not if otherwise.                                                                                              |
| 0         | Type          | Packet is a 'response' when it's asserted.                                                                                                     |

### 7.1.1. Response Code

| Code    | Name     | Description                                                                                                                                                                                                                                                                                                                                              |
| ------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `2'b00` | OKAY     | **OKAY.** Indicates there was no error on previous event. Issued operation is guaranteed to be succeed.                                                                                                                                                                                                                                                  |
| `2'b01` | RECERR   | **Recipient Error.** Indicates there was an error on previous event.<br>When this happens, the recipient must reject the operation which was issued by that event and cancel rest of operation if it was a multi-flit event.<br>- For read operation, recipient responds back with `pvalid` = 0.<br>- For write operation, recipient cancels the change. |
| `2'b10` | DECERR   | **Decoder Error.** Indicates there was no corresponding recipient with provided address. Any operation issued by event has no effect and canceled if it was a multi-flit event.<br>- For read operation, a tile responds back with `pvalid` = 0.<br>- For write operation, it has no effect.                                                             |
| `2'b11` | Reserved | *Reserved*                                                                                                                                                                                                                                                                                                                                               |

## 7.2. Event

![[Event Packet Bit field.png]]

| Bit index | Name       | Description                                |
| --------- | ---------- | ------------------------------------------ |
| 23:8      | Payload    | Field for some events which sets value.    |
| 7:6       | Reserved   | *Reserved*                                 |
| 5:1       | Event type | An event type.                             |
| 0         | Type       | Packet is an 'event' when it's deasserted. |

### 7.2.1. Event List

#### 7.2.1.1. Non-control event

| Code       | Name     | Length | Description                                                                                                               |
| ---------- | -------- | ------ | ------------------------------------------------------------------------------------------------------------------------- |
| `5'b00000` | Spike    | 1      | When arrived, any design that is `Nero-P` compliant must update the membrane potential with associated weight $w$.        |
| `5'b00001` | Dopamine | 1      | When arrived, any design that is `Nero-D` compliant must update the dopamine buffer. Otherwise, this event has no effect. |

#### 7.2.1.2. Control event

| Code       | Name                        | Length | Description                                                                                                                                                                                                                                                                                                                                                                                                     |
| ---------- | --------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `5'b10000` | Get settings                | 1      | When arrived, any design that is `Nero-P` compliant should respond with 16-bits settings register value.                                                                                                                                                                                                                                                                                                        |
| `5'b10001` | Get $k_1$                   | 1      | When arrived, any design that is `Nero-P` compliant should respond with 16-bits first-order decaying coefficient $k_1$ register value.                                                                                                                                                                                                                                                                          |
| `5'b10010` | Get $k_2$                   | 1      | When arrived, any design that is `Nero-P` compliant should respond with 16-bits second-order decaying coefficient $k_2$ register value.                                                                                                                                                                                                                                                                         |
| `5'b10011` | Get pending log count       | 1      | When arrived, any design that is `Nero-T` compliant should respond with pending log count which is representable with up to 16 bits. Otherwise, this event has no effect.                                                                                                                                                                                                                                       |
| `5'b10100` | Get dopamine length         | 1      | When arrived, any design that is `Nero-D` compliant should respond with current dopamine buffer level which is `DOPAMINE_BUFFER_WIDTH` bits long. <br>Otherwise, this event has no effect.                                                                                                                                                                                                                      |
| `5'b10101` | Get eligibility $k_{e1}$    | 1      | When arrived, any design that is `Nero-L` compliant should respond with  first-order eligibility decaying coefficient $k_{e1}$.<br>Otherwise, this event has no effect.                                                                                                                                                                                                                                         |
| `5'b10110` | Get eligibility $k_{e2}$    | 1      | When arrived, any design that is `Nero-L` compliant should respond with 16-bits second-order eligibility decaying coefficient $k_{e2}$. <br>Otherwise, this event has no effect.                                                                                                                                                                                                                                |
| `5'b10111` | Get log destination         | 1      | When arrived, any design that is `Nero-T` compliant should respond with log packet destination that is up to 16 bits.<br>Otherwise, this event has no effect.                                                                                                                                                                                                                                                   |
| `5'b11000` | Get connections             | N      | When arrived, any design that is `Nero-C` compliant should respond with 16-bit, multi-flit response for every entries registered. Otherwise, this event has no effect.<br>For every successful retrieval, this should respond with response code OKAY and corresponding connection payload.<br>This is a blocking operation, so before all entries are enumerated every other incoming events will get stalled. |
| `5'b11001` | Get log auto-flush settings | 1      | When arrived, any design that is `Nero-T` compliant should respond with 16-bits automatic log flushing settings. Otherwise, this event has no effect.                                                                                                                                                                                                                                                           |
| `5'b11010` | Get refractory period       | 1      | When arrived, any design that is `Nero-R` compliant should respond with 16-bits refractory period register value. Otherwise, this event has no effect.                                                                                                                                                                                                                                                          |
| `5'b11011` | Get destination connections | N      | When arrived, any design that is `Nero-C` compliant should respond with 16-bit, multi-flit response for every 'destination' entries registered. Otherwise, this event has no effect.<br>This is a blocking operation, so before all entries are enumerated every other incoming events will get stalled.                                                                                                        |


| Code           | Name                        | Length | Description                                                                                                                                                                                                                                                                                                                                                                   |
| -------------- | --------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `5'b00010`     | Set settings                | 1      | When arrived, any design that is `Nero-P` compliant should update 16-bits settings register with supplied payload.                                                                                                                                                                                                                                                            |
| `5'b00011`     | Connect                     | 2      | When arrived, any design that is `Nero-C` compliant should add destination and associated weight $w$ in order. Otherwise, this event has no effect.                                                                                                                                                                                                                           |
| `5'b00100`     | Set $k_1$                   | 1      | When arrived, any design that is `Nero-P` compliant should update `WEIGHT_WIDTH` bits long first-order decaying coefficient $k_1$ with supplied payload.                                                                                                                                                                                                                      |
| `5'b00101`     | Set $k_2$                   | 1      | When arrived, any design that is `Nero-P` compliant should update `WEIGHT_WIDTH` bits long second-order decaying coefficient $k_2$ with supplied payload.                                                                                                                                                                                                                     |
| `5'b00110`     | Flush log                   | 1      | When arrived, any design that is `Nero-T` compliant should send every pending logs to destination. Otherwise, this event has no effect.<br>This is a blocking operation, so until every logs are pushed out every other events will get stalled.<br>Be sure to set the correct destination before calling this, otherwise it's *unpredictable* how these log packets will be. |
| `5'b00111`     | Set log destination         | 1      | When arrived, any design that is `Nero-T` compliant should update log destination with supplied payload which is up to 16 bits. Otherwise this has no effect.                                                                                                                                                                                                                 |
| `5'b01000`     | Set dopamine length         | 1      | When arrived, any design that is `Nero-D` compliant should update dopamine length which is `DOPAMINE_BUFFER_WIDTH` bits long with supplied payload.<br>Otherwise this has no effect.                                                                                                                                                                                          |
| `5'b01001`     | Set eligibility $k_{e1}$    | 1      | When arrived, any design that is `Nero-L` compliant should update `E_BUFFER_WIDTH` bits long first-order eligibility decaying coefficient $k_{e1}$. <br>Returns error when it's greater than `E_BUFFER_WIDTH`.<br>Otherwise this event has no effect.                                                                                                                         |
| `5'b01010`     | Set eligibility $k_{e2}$    | 1      | When arrived, any design that is `Nero-L` compliant should update `E_BUFFER_WIDTH` second-order eligibility decaying coefficient $k_{e2}$. <br>Returns error when it's greater than `E_BUFFER_WIDTH`.<br>Otherwise this event has no effect.                                                                                                                                  |
| `5'b01011`     | Set log auto-flush settings | 1      | When arrived, any design that is `Nero-T` compliant should update 16-bits automatic log flushing settings. Otherwise, this event has no effect.                                                                                                                                                                                                                               |
| `5'b01100`<br> | Set refractory period       | 1      | When arrived, any design that is `Nero-R` compliant should update refractory period register which is `R_PERIOD_WIDTH` bits long  with supplied payload. Otherwise, this event has no effect.                                                                                                                                                                                 |
| `5'b01101`     | Clear destinations          | 1      | When arrived, any design that is `Nero-C` compliant should remove connections associated with given destination neuron. Otherwise, this event has no effect.                                                                                                                                                                                                                  |
| `5'b01110`     | Add destination             | 1      | When arrived, any design that is `Nero-C` compliant should store arrived destination coordinate so that it can be sequenced later once neuron is spiked. Otherwise, this event has no effect.                                                                                                                                                                                 |
