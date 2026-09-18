FROM ubuntu:24.04

# Bundle the skill under test into the image. task.toml points
# environment.skills_dir at /skills so Harbor hands it to the agent.
COPY skills/ /skills/

WORKDIR /app
