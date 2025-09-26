# Agent Coordination Hub

This file coordinates multiple parallel workstreams for documenting and modernizing the CICS GenApp system.

## Mainline Development Tasks

### Current Active Work
- **PHASE 1 COMPLETE:** Documented all core transaction front-end programs and their immediate dependencies:
  - Customer operations: `LGACUS01` (add), `LGICUS01` (inquire), `LGUCUS01` (update) with backing services `LGACDB01`, `LGACVS01`
  - Policy operations: `LGAPOL01` (add), `LGIPOL01` (inquire), `LGUPOL01` (update), `LGDPOL01` (delete) with backing services `LGAPDB01`, `LGAPVS01`
  - All front-end programs follow consistent patterns: commarea validation, request ID checking, backend delegation, error logging via `LGSTSQ`

### Next Milestones
- [ ] **Phase 2 - Data Services:** Document backend DB modules (`LGAPDB01`, `LGDPDB01`, `LGIPDB01`, `LGUCDB01`) and shared logging (`LGSTSQ`)
- [ ] **Phase 3 - Integration Testing:** Validate documented transaction flows end-to-end
- [ ] **Phase 4 - Modernization Planning:** Define API interfaces and refactoring opportunities

## Full Documentation Branch Tasks

### Dependency Analysis & Visualization
- [x] Created dependency graph visualization tool (`tools/visualize_dependencies.py`)
- [x] Generated current state visualization (`tools/dependency_graph_current_state.png`)
- [x] Identified documentation priorities based on dependency analysis

### Documentation Priority Recommendations

Based on dependency graph analysis (26 nodes, 39 edges):

#### High Impact Foundation Components (Document First)
1. **LGCMAREA** (copybook): 11 dependents - Shared commarea layout
   - *Critical:* Used by all transaction programs for communication
2. **LGSTSQ** (cobol): 11 dependents - TDQ logger for diagnostics  
   - *Critical:* Central logging facility used throughout system

#### Core Backend Services (Document Next)
3. **LGAPDB01** (cobol): Complex component with 9 dependencies - DB2-backed policy add service
   - *Key integration point:* Orchestrates policy creation across multiple DB2 tables
4. **LGACDB01** (cobol): 4 dependencies - Add customer DB2 backend service
   - *Customer domain leader:* Handles customer data persistence

### Parallel Documentation Streams

#### Stream A: Shared Assets (Can work independently)
- [ ] **Copybooks:** `LGCMAREA`, `POLLOOK`, `POLLOO2`, `SOA*` structures
- [ ] **BMS Maps:** `SSMAP.bms` screen definitions and field mappings
- [ ] **SQL Includes:** `LGPOLICY` host variable definitions

#### Stream B: Operations & Automation (Can work independently)
- [ ] **JCL Inventory:** Map every member in `base/cntl/` to compile/deploy functions
- [ ] **REXX Automation:** Document `base/exec/` scripts and their trigger points
- [ ] **Deployment:** Analyze `install.sh` dataset allocation and upload process

#### Stream C: Data & Simulation (Can work independently)
- [ ] **Test Data:** Document `base/data/` sample datasets and their relationships
- [ ] **Simulation Flows:** Map `base/wsim/` workstation simulator scenarios
- [ ] **Customer Journeys:** Trace complete business processes through the system

## Progress History

### Recent Achievements
- Documented `LGAPOL01` (Add Policy COBOL program) and captured dependencies in the README and dependency graph store
- Drafted documentation roadmap with sequencing and parallel work suggestions
- Reviewed and documented `LGAPVS01` and `LGAPDB01`, noting VSAM and DB2 responsibilities plus shared error pathways
- Created comprehensive dependency visualization and analysis tools

## Dependency Notes

### Key Relationships
- `LGAPOL01` depends on `LGAPDB01` (database insert logic), `LGSTSQ` (TDQ logging helper), and the `LGCMAREA` copybook
- `LGAPVS01` writes to VSAM cluster `KSDSPOLY`, consumes `LGCMAREA`, and logs via `LGSTSQ`
- `LGAPDB01` relies on DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`, `COMMERCIAL`), invokes `LGAPVS01`, and uses `LGPOLICY`/`LGCMAREA` copybooks plus `LGSTSQ` for diagnostics
- Customer front-ends (`LGACUS01`, `LGICUS01`, `LGUCUS01`) all depend on corresponding DB backends (`LGACDB01`, `LGICDB01`, `LGUCDB01`) and shared infrastructure (`LGSTSQ`, `LGCMAREA`)
- Policy front-ends (`LGAPOL01`, `LGIPOL01`, `LGUPOL01`, `LGDPOL01`) follow similar patterns with DB backends (`LGAPDB01`, `LGIPDB01`, `LGUPDB01`, `LGDPDB01`)
- All transaction programs share error logging through `LGSTSQ` and use `LGCMAREA` for consistent commarea structure

## Tooling

### Dependency Graph Management
- **Core tool:** `tools/dep_graph.py` (CLI for managing `dependency_graph.json`)
- **Visualization:** `tools/visualize_dependencies.py` (generates current state diagrams)
- **Usage examples:**
  - Add/update a node: `./tools/dep_graph.py add-node <NAME> --type <category> --description "..." --depends-on dep1 dep2`
  - Create an edge later: `./tools/dep_graph.py add-edge <SOURCE> <TARGET>`
  - Inspect a node: `./tools/dep_graph.py show <NAME> --include-dependents`
  - List nodes by type: `./tools/dep_graph.py list --type cobol`
  - Generate visualization: `python3 tools/visualize_dependencies.py --stats --suggestions`

## Coordination Guidelines

### For Mainline Development
- Focus on serial progression through transaction programs
- Pair front-end and back-end modules in same development cycle
- Update dependency graph as new relationships are discovered
- Coordinate with parallel streams for shared component updates

### For Full Documentation Branch
- Work can proceed in parallel across the three streams (A, B, C)
- Shared components (Stream A) should be documented early to support other streams
- Cross-reference findings with the mainline development discoveries
- Regular sync points to ensure consistency across workstreams

### Communication
- Update this file with progress on each stream
- Use dependency graph to track impact of changes
- Document any architectural insights that affect multiple streams
