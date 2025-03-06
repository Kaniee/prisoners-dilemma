# About
This is toy project to host a tournament where different strategies (docker images) can compete in the prisoner's dilemma.

# Usage
Start the Docker registry, the PostgreSQL database and finally the FastAPI application
```bash
make registry
make database
make app
```

Add strategies using the cli
```bash
./scripts/strategy_cli.sh add <Strategy name> <docker image name>
```

# Status
It lacks a couple of things:
- Documentation
    - Getting started
    - Architecture
    - Usage manual
    - Rules
    - Strategy requirements
- Features
    - Configurable and jittered number of turns in round
    - Live updates to pages
    - Improved layout
    - Improved strategy management
    - Add debugging information to front end, e.g. timeout
    - Configurable "Miscommunication" probability
    - Show "Miscommunication" on front end
- Tests
- Cleanup

I might come back to this at some point, until then this repo is meant for my colleagues who participated in the tournament, to look behind the curtain.
