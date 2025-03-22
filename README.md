# Site Sentry - Autonomous Website Maintenance Framework

Site Sentry is a powerful framework for autonomous website maintenance, featuring a multi-agent architecture that handles content updates, SEO optimization, error fixing, and more.


## Features
-   Local setup tool with CLI interface & config for ease of use & control
-   Cloud Service with [Site Sentry](https://sitesentry.metacatalyst.in/) provides quick setup with minimal config
-   Optimise website performance, SEO, error & linting
-   Get insights on bottlenecks on your web apps, get them fixed with Code LLMs.
-   Integration with Github (Personal Access Token), safe changes to new branches.
-   Integration with state of the art LLMs: Anthropic Claude, Google Gemini, OpenAPI, etc..

<br />

## Using the tools.

### Pre-requisities (external APIs)
> These APIs aren't paid, all shown in demo here are free of use, and needed for use throughout, so easier to get them in advance:
- Github:  Personal Access Token
- Google: Gemini API


<br /> <br />

**There's two ways to use it:**

### A. As a framework / tool - local:
> Setup locally using a python tool, comes with CLI + config 


```bash
pip install git+asdhs.com
```

.
<br />

### B. As a service - cloud:
> Use our provided web interface to host background tasks, via cron or CI/CD

<be />

> [!TIP]
> After reading these two steps, if you're wondering: Is there any difference between the two? No internally they do the same action, its your choice on which is more suitable.
> - More control & changes needed?  local
> - Quick setup & analsis?  cloud

<br />


## Architecture

### Agents

Internally, the framework uses LLM agentic system built on top of [LangChain](https://www.langchain.com/) and [LangGraph](https://www.langchain.com/langgraph)

![agents-architecture](https://github.com/user-attachments/assets/dc28233e-151f-41a4-aeb0-ad8e2f6e9ebb)

1. **READ Agent**
   - Given a target site, recursively indexes (using [get-site-urls](https://www.npmjs.com/package/get-site-urls) )
   - Reads audits from lighthouse & webhint to find issues.

3. **Manager Agent**
   - Orchestrates workflow using LangGraph
   - Coordinates between specialized agents
   - Handles task delegation and error recovery

4. **Specialized Agents**
   - Content Update Agent: Updates outdated content
   - Error Fixing Agent: Detects and fixes issues
   - SEO Optimization Agent: Enhances metadata and structure
   - Content Generation Agent: Creates new content
   - Performance Monitoring Agent: Tracks metrics

5. **Deployment Agent**
   - Manages GitHub integration
   - Handles branch creation and merging
   - Runs automated tests

### Memory Management

- Uses ChromaDB for persistent memory & storage
- Maintains conversation and document memory
- Supports context retrieval and similar interaction searching

<br />


### [Site Sentry](https://sitesentry.metacatalyst.in/) - Service


![site-sentry-architecture](https://github.com/user-attachments/assets/b71ac9b2-c42a-4599-b72e-23cc085600cd)

Site-Sentry acts as a service wrapper around the sentry framework (the tool), which is easier to setup & provides more features like: <br />
1. CI/CD trigger - changes when any push to a branch in github repo
2. CRON job - interval use the framework, make updates in batches
3. Analysis via Page Speed Insights API on target site.

> These can also be done via tool, but needs to be setup manually

<br />


##### Sentry Dashboard

For example, [this site](https://palinifoundation.vercel.app/) is reported on the dashboard after analysis:

![site-sentry-dashboard](https://github.com/user-attachments/assets/7ae7fe82-7c8d-4315-8296-8b4038947ef4)


##### Sentry Job

A "Sentry Job" is a background process you can add, to trigger either via CI/CD or CRON job. 




