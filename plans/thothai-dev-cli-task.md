# Task: Development CLI Implementation

## Objective
Create a unified development CLI (`thothai-dev`) to replace all shell scripts (.sh, .ps1) in the root directory for build, push, deploy, and management operations.

## Analysis Phase
- [x] List all .sh and .ps1 scripts in root
- [x] Analyze each script's functionality
- [x] Review existing CLI architecture (`thothai-cli`, `thothai-data-cli`)
- [x] Review helper scripts in `scripts/` directory
- [x] Create implementation plan

## Decision Points (pending)
- [ ] Confirm Docker Compose files move to `docker/`
- [ ] Choose Docker SDK vs subprocess approach
- [ ] Define implementation timeline (all-at-once vs incremental)

## Implementation Phase

### Phase 1: CLI Foundation
- [ ] Create CLI package structure `cli/thothai-dev/`
- [ ] Implement `build` command
- [ ] Implement `push` command
- [ ] Test equivalence with `push.sh`

### Phase 2: Docker Operations
- [ ] Implement `compose install/up/down/logs` commands
- [ ] Implement `swarm install/status/update/rollback/logs/backup` commands
- [ ] Move Docker Compose files to `docker/`
- [ ] Update all references

### Phase 3: Local Development
- [ ] Implement `dev start` command
- [ ] Implement `dev stop/restart/status` commands
- [ ] Implement `config validate/generate/show` commands

### Phase 4: Cleanup
- [ ] Update documentation (GEMINI.md, README.md)
- [ ] Remove shell scripts from root
- [ ] Final verification

## Related Files
- Plan: [thothai-dev-cli-plan.md](file:///Users/mp/ThothAI/plans/thothai-dev-cli-plan.md)
- Existing CLIs: `cli/thothai-cli/`, `cli/thothai-data-cli/`
- Scripts to replace: `push.sh`, `install.sh`, `install-swarm.sh`, `manage-swarm.sh`, `start-all.sh` (and .ps1 equivalents)
