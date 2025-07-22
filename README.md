# PIPKA 

<div align="center">
  
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/mirecekdg)

</div>

PIPKA started as project to help my daughter to bring AI to execute code in "simple way". 

How it is going now you can check in this project.

This project now should be deprecated as all similar things can do AI agents with MCP, but I am flushing it to github.com for references of my work.

Project is reworked from https://github.com/blazzbyte/OpenInterpreterUI

I'am not working on PIPKA anymore, you can fork and work on your own.

## PIPKA's name

When my family started to use PIPKA on daily basis (before it installed everyting into it) they complained about pipping (pip install xxx) before tasks. And this is why we were calling this software PIPKA.

## Introduction

PIPKA is a project aimed at simplifying the process of running code and interacting with AI models through a graphical user interface (GUI) and voice. With Streamlit as the frontend framework, this tool provides an intuitive way to work with Python/C/R/Go/pascal/fortran/cobol and AI applications without needing to write code in a traditional coding environments.

You can chat with PIPKA through interface similar to ChatGPT interface in your web browser.
This provides a natural-language interface for your day-to-day activities or simplyfi your work.
And what PIPKA is not able to solve, it can write and run script/program for you.

**Watch PIPKA like a self-driving car, and be prepared to end the process by closing browser window or hit the stop button.**

## Features

- User-friendly GUI and voice interface for running Python and other programming/scripting language codes
- Integration with Amazon Bedrock AI applications for natural language processing and chatbot functionalities.
- Simplified execution of code and interaction with Amazon Bedrock AI models.
- Customizable and extensible for different use cases.

### PIPKA user features
- uses LiteLLM chat models (I am using Anthropic Claude 4 Sonet, 3.5 Haiku; OpenAI GPT-4.x, o3) with all their capabilites like vision and file understanding
- has persistent storage for your files (independent on container)
- has a chat memory - you can continue in conversation
- can plot, clean and analyze large datasets - no problem to expand space on local filesystem
- can install and controll browsers
- every PIPKA user has it's own space and configuration independent to other environments
- speech to text (you can talk to PIPKA)

- interacts with cloud APIs (you can configure your AWS SSO for example, Google CLI, Azure CLI)
- can connect via SSH/SSM to servers

## Docker Deployment

To run PIPKA using Docker, use the following command:

```bash
docker run --detach --name pipka -p 8501:8501 -v /home/$USER/pipka-workspace/:/app/workspace -e USEREK="ai@mirecek.org" ghcr.io/mirecekd/pipka:latest
```

This will:
- Run the container in detached mode with name "pipka"
- Expose the application on port 8501
- Mount your local `~/pipka-workspace` directory to the container's workspace
- Set the user email environment variable
- Use the latest multi-architecture image supporting AMD64 (almost everywhere) and ARM64 platforms (AWS Gravitron or for example Raspberry PI4+)