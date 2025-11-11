# sNPU Nero

Nero is a Spiking Neural Processing Unit(sNPU) designed to accelerate [[Spiking Neural Network (SNN)]]. It's designed to address existing [[Deep Neural Network]] models' limitation technically:

> Large models are increasingly expensive and inefficient to train.

But also aims to become 'personal alternative' against the centralized, dominant AI paradigm. Modern large-scale AIs raise two fundamental questions:

1. **How** are they trained?
2. **Where** does their training data come from?

Both the pre/post-training process are largely closed to the public, so we rely on speculation and second-hand reports at best. Meanwhile, the DNN's philosophy: "The more data, the better" has made these systems voracious data consumers, often at the expense of individuals' privacy.

## What Nero Ecosystem offers

Nero ecosystem, from sNPU hardware to Synthesizer toolchain, proposes a different path grounded in transparency, autonomy and accessiblity. What can already be done with local DNNs become simpler, clearer and more personal with Nero:

1. **You decide how to train.**
		Feed your own spike stimuli with your own configuration. You can even tweak the sNPU architecture itself if you wish. Everything is open and under your control.
2. **You decide what to train on.**
		Keep data personal and local, share selectively among trusted peers or collaborate globally by exchanging models, inputs and configurations.

With a physical substrate(sNPU itself) and growing library of discovered models and datasets, whether it's yours or community's, Nero ecosystem helps anyone to begin right away.

Rather than relying on centralized AI infrastructure, Nero ecosystem aspires to **empower the individuals**: enabling users to build, exchange and federate self-learning systems at low cost. All open, inspectable and truly their own.

# Nero's Philosophy

## Nero as an 'explorer' on continuum of learning

Refer: [[Spectrums of Learning]]

Learning is not a binary subject. [[Gradient Descent]](GD), [[Evolutionary Algorithm]](EA) and [[STDP]] just occupy different regions of the same continuum and Nero's role is to explore this landscape experimentally. It does not fit a single model to task-ready, but it **discovers that very candidates themselves**.

In Nero ecosystem, an optimization is a *post-hoc* process. Given high-level objectives and constraints, Nero first searches the space to uncover 'viable' structures. Then it lets user take an extra mile with discovered models. It's up to user to discard, prune or even compose with other models to test its capability to extreme degree.

## The call of 'synthesizer'

Nero is designed to be a standalone, discrete peripheral connected with host environment. Whether it's being shipped on FPGA, ASIC or whatever possible does not matter.

Nero alone can't do anything. Someone must instruct to make it work. However unlike the conventional compilers which translate high-level language construct to something more machine-level friendly, Nero must walk in the opposite direction.

Compilers already know the code written by user and *user knows what it does*. Their objective is simply, "Make it the most efficient form". Nero Compiler, on the other hand, has no information but a high-level objective and constraints. There's no explicit instruction, like code to achieve the goal.

Also, unlike the typical DNN models which introduce new block for different needs, Nero just have to rewire the underlying SNN neurons. Typical [[Neural Architecture Search]](NAS) falls short for big models and assumes user's knowledge about their models, but Nero's approach dramatically lowers the hurdle for discovering new models as it only asks user a 'goal' and 'constraints', therefore help users find a scalable approach easily while physical limit allows.

That is, a typical compiler runs top-down. Nero compiler is the opposite: "bottom-up". This makes the Nero compiler not an ordinary compiler: *A morphogenetic model explorer*, or ***synthesizer*** if it's called.

# Flow

1. User define the high-level goals and constraints. It's up to user's call how to lower down such 'requirement' into explicit and precise extent. (Goal and constraint definition)
2. Once a goal is established, the Nero synthesizer then places neuron randomly or given preset. (Initialization)
3. Given an input stimuli, neurons on Nero will spike and emit an output over time. after it's finished it'll check if it meets a goal requirement. (Test) 
4. If it succeeded, mark it as 'complete' and report. (Finish)
5. Otherwise, Nero synthesizer changes neuron arrangement and parameters and run it again. Run until it hits the constraint limit or timeout. (Evolution)
6. If everything fails, mark it as 'failed' and report (Finish)

# License

Nero is released under the MIT License: fully open, modifiable, and free for any purpose.

This project was created with a single guiding principle:

> Knowledge and learning architectures should be open to all.

The value of Nero lies not in exclusivity, but in accessibility. You are free to use, extend, or commercialize this work, as long as credit to the original author is preserved.

# Contact

Gerald Nelson (nergy_nelson@proton.me)
