---
hide:
  - toc
---

<style>
  .md-content__inner h1 { display: none; }
</style>

<div align="center" markdown="1">
<div id="wallpaper" alt="OpenCrate Wallpaper"></div>
<p id="wallpaper-tagline">True plug-and-play interoperability for orchestrating AI workflows.</p>

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/OpenCrateAI/opencrate/release-pypi.yml?style=flat-square&logo=python&logoColor=%23fff)
![PyPI - Version](https://img.shields.io/pypi/v/opencrate?style=flat-square&logo=python&logoColor=%23fff)
![GitHub commit activity (branch)](https://img.shields.io/github/commit-activity/w/OpenCrateAI/opencrate/main?style=flat-square&logo=github)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/opencrate?style=flat-square&logo=python&logoColor=%23fff)
</div>

OpenCrate is an [open-source](https://github.com/OpenCrateAI/opencrate) framework that lets you easily develop your AI workflows and its modules into isolated, self-contained runtimes and expose them as native, composable building blocks. This enables you, your team, and the open-source community to build AI workflows more efficiently and focus on architectures, metrics, and intelligence by seamlessly integrating existing tools and utilities into unified workflows, eliminating dependency conflicts, environment setups, integration headaches.

With OpenCrate, your modules become reusable assets that you and your team can grab and plug into any workflow. You can "call a module" running on a completely different Python version or dependency stack as if it were a standard library function.

Every tool or utility you build - whether it cleans data, generates embeddings, detect sentiments or runs evaluations - should help you with every project, not just the current one. OpenCrate enables, you, your team, and the open-source community to facilitate each other's progress, creating a truly interoperable ecosystem with turning isolated, one-off scripts into tools that anyone can actually use without the integration failures.


## **__Picture This__**
You stumble upon **the perfect** research paper or a brilliant GitHub project. It solves exactly the problem you've been banging your head against for a week. You clone the repo, crack your knuckles, and get ready to integrate this new finding directly into your existing workflow.

And here's how the story usually ends for your integration:

- The new module demands **TensorFlow 1.x** and **Python 3.8**.
- Your current stack is happily running **PyTorch 2.2** on **Python 3.12**.
- The CUDA driver dependency conflicts start fighting with your GPU.
- And the pip installs? It turns into a battle royale where no library wins.

With this, you're left with one of these *frustratingly common* follow-ups:

- You either rage quit because who rewrites their entire stack "in the hope" that something magical is gonna happen?
- Instead of making actual progress, you spend hours - if not days - fixing environments, dependencies and import errors or even **rewriting perfectly good code just to make it fit**.

What you **wanted** to do is below:

<div align="center">
<img src="assets/without-opencrate.png" class="mkdocs-img"/>
</div>

Yep, this does look a little scary to solve, doesn't it? **If only we could:**

- **Encapsulate each conflicting module** within a self-contained, isolated runtime leveraging containerization to ensure zero conflicts for python or for any system dependency like cuda.
- **Invoke functions across environments** as if they were native Python calls, completely abstracting away the underlying dependency conflicts.
- **Auto-orchestrate a microservices architecture** where modules communicate over optimized protocols without us needing to write a single line of networking boilerplate.
- **Seamlessly transport complex payloads** like Tensors, DataFrames, Texts, Images and more, between services without worrying about serialization and type conversions.
- **Auto-scale services dynamically based on load** ensuring zero performance bottlenecks by automatically spinning up additional resources for high-demand modules while keeping the rest efficient.

Ahah, that's exactly what we've built.

## **__Working with OpenCrate__**

<div align="center">
<img src="assets/with-opencrate.png" class="mkdocs-img"/>
</div>

We're working towards building an ecosystem where every AI workflow you create, you get to spend most time on innovation rather than the legwork. Our approach is quite simple: containarization, orchestration and abstraction. 

### __**Encapsulate each conflicting module**__

```bash
oc init
```

### __**Invoke functions across environments**__

```python
from opencrate import OpenCrateServer, 

my_custom_eda = OpenCrateClient("braindotai/my-custom-eda:v3")
eda_results = my_custom_eda.perform_eda(dataframe)
```

### __**Auto-orchestrate a microservices architecture**__

...`

### __**Seamlessly transport complex payloads**__

...

### __**Auto-scale services dynamically based on load**__

...


<br>
<br>
<br>