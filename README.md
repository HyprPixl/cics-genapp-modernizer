# CICS GenApp Modernizer

## Overview
- Modernization workspace for the IBM CICS GenApp sample application and supporting assets.
- Contains legacy COBOL programs, JCL procedures, REXX utilities, and data used to simulate the insurance workload.
- Goal: inventory and document the moving parts before proposing upgrades or refactors.

## Repository Layout
- `base/src/` legacy sources: COBOL programs (`lg*.cbl`), copybooks (`*.cpy`), BMS maps (`ssmap.bms`), and supporting text assets.
- `base/cntl/` JCL members for compiling programs, allocating datasets, and driving GenApp jobs.
- `base/exec/` REXX execs invoked during build or operations (`cust1.rexx`, `mac1.rexx`).
- Customer Experience Assets: `base/wsim/` workstation simulator flows, `base/event-bindings/` CICS event bindings, and `base/images/` reference diagrams.
- `base/bin/` utilities, notably `install.sh`, to allocate host datasets and upload members via `tsocmd` and USS `cp`.
- `base/data/` sample input datasets (`ksdscust.txt`, `ksdspoly.txt`) referenced by the application.

## Documentation Work Breakdown
- Legacy Programs: walk each `lg*.cbl` module, record purpose, entry points, and copybook usage.
- Shared Copybooks & Maps: describe `*.cpy` data structures and `ssmap.bms` screen definitions.
- Operations JCL: map every member in `base/cntl/` to its function (compile, bind, housekeeping, etc.).
- Automation & Tooling: review REXX execs and `install.sh` for deployment or setup automation.
- Data & Simulation Assets: capture how `data/` and `wsim/` files drive scenarios or tests.
- Platform Integrations: document `event-bindings/` artifacts and any external dependencies.

## Legacy Program Notes
### LGAPOL01 – Add Policy Transaction
- Purpose: front-end CICS task for creating a new insurance policy; validates commarea length before delegating persistence to `LGAPDB01`.
- Interfaces: expects `DFHCOMMAREA` shaped by `LGCMAREA` (minimum 28-byte header plus request payload) and initializes `CA-RETURN-CODE` to `00` on entry.
- Dependencies: `LGAPDB01` (database insert), `LGSTSQ` (TDQ error logging), `LGCMAREA` copybook for shared structures, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with code `LGCA` when no commarea provided; writes timestamped diagnostic entries via `LGSTSQ` and echoes failing commarea payload.
- Follow-ups: document `LGAPDB01` data-handling logic and confirm expected commarea layout for policy adds.

### LGAPVS01 – Policy VSAM Persistence Helper
- Purpose: writes policy summary records into VSAM KSDS `KSDSPOLY` after `LGAPDB01` allocates a policy number.
- Interfaces: consumes `LGCMAREA` to drive record keys/segments; expects `CA-REQUEST-ID` to provide policy type discriminator (`C`, `E`, `H`, `M`).
- Dependencies: VSAM file `KSDSPOLY`, `LGSTSQ` for TDQ logging, `LGCMAREA` copybook, CICS file control APIs.
- Error Handling: non-normal `RESP` results set `CA-RETURN-CODE` to `80`, log failure via `LGSTSQ`, and return without abend to allow caller control.
- Notes: ensures commarea snapshots go to TDQ on failure, preserving the request data used to build the record image.

### LGAPDB01 – Policy Database Writer
- Purpose: core add-policy back-end that inserts rows across DB2 tables before invoking `LGAPVS01` for VSAM replication.
- Interfaces: requires `LGCMAREA` payloads matching add-policy templates (`01AEND`, `01AHOU`, `01AMOT`, `01ACOM`); includes SQL copybook `LGPOLICY` for host variable definitions.
- Dependencies: DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`, `COMMERCIAL`), `LGAPVS01` (post-insert VSAM sync), `LGSTSQ` for logging, `LGCMAREA`, `LGPOLICY` SQL include, CICS DB2 commands (`EXEC SQL`), and TDQ infrastructure.
- Error Handling: translates SQLCODEs into GenApp return codes (`70`, `90`), logs details through `LGSTSQ`, and abends with `LGSQ` on downstream table failures to trigger unit-of-work backout.
- Notes: fetches generated policy number via `IDENTITY_VAL_LOCAL()` and updates commarea so caller can return the new identifier.

### LGACUS01 – Add Customer Transaction
- Purpose: front-end CICS task for creating a new customer record; validates commarea structure before delegating persistence to `LGACDB01`.
- Interfaces: expects `DFHCOMMAREA` shaped by `LGCMAREA` with customer data payload; initializes `CA-RETURN-CODE` to `00` and `CA-NUM-POLICIES` to `00` on entry.
- Dependencies: `LGACDB01` (database insert), `LGSTSQ` (TDQ error logging), `LGCMAREA` copybook for shared structures, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with code `LGCA` when no commarea provided; returns code `98` for insufficient commarea length; writes timestamped diagnostic entries via `LGSTSQ`.
- Follow-ups: document `LGACDB01` data-handling logic and confirm expected commarea layout for customer adds.

### LGACDB01 – Customer Database Writer
- Purpose: DB2-backed customer add service that inserts customer records and invokes VSAM replication and security services.
- Interfaces: requires `LGCMAREA` with customer details; uses `LGPOLICY` copybook for field definitions and DB2 host variables.
- Dependencies: DB2 `CUSTOMER` table, `LGACVS01` (VSAM sync), `LGACDB02` (customer security), named counter `GENACUSTNUM` from pool `GENA`, `LGSTSQ` for logging, `LGCMAREA` copybook.
- Error Handling: handles counter unavailability by using DB2 `DEFAULT` for customer number assignment; translates SQLCODEs to return code `90`; logs SQL requests and results.
- Notes: attempts to obtain customer number from CICS named counter first, falls back to DB2 identity generation; updates commarea with assigned customer number.

### LGACDB02 – Customer Security Service
- Purpose: specialized customer security service that manages customer authentication credentials in the `CUSTOMER_SECURE` table.
- Interfaces: uses custom commarea structure with customer number, encrypted password, security state indicator, and password change count fields.
- Dependencies: DB2 `CUSTOMER_SECURE` table, `LGCMAREA` and `LGPOLICY` copybooks for data structures, `LGSTSQ` for error logging.
- Error Handling: validates request ID (`02ACUS` for new customer security add), returns `99` for unrecognized requests, `98` for SQL insertion failures.
- Notes: handles secure customer credentials separately from main customer profile; supports password state management and change tracking; integrates with main customer add workflow via `LGACDB01`.

### LGACVS01 – Customer VSAM Writer
- Purpose: writes customer summary records into VSAM KSDS `KSDSCUST` after `LGACDB01` processes DB2 customer insertion.
- Interfaces: consumes `LGCMAREA` customer data starting from `CA-Customer-Num`; expects 225-byte customer record format.
- Dependencies: VSAM file `KSDSCUST`, `LGSTSQ` for TDQ logging, `LGCMAREA` copybook, CICS file control APIs.
- Error Handling: non-normal file `RESP` results set `CA-RETURN-CODE` to `80`, log failure details via `LGSTSQ`, and abend with `LGV0` to preserve transaction integrity.
- Notes: uses customer number as both record key and starting field; ensures diagnostic data includes RESP/RESP2 codes for file operation troubleshooting.

### LGICUS01 – Inquire Customer Transaction
- Purpose: front-end CICS task for retrieving customer information; validates commarea structure before delegating lookup to `LGICDB01`.
- Interfaces: expects `DFHCOMMAREA` shaped by `LGCMAREA` with customer inquiry payload; initializes `CA-RETURN-CODE` to `00` and `CA-NUM-POLICIES` to `00` on entry.
- Dependencies: `LGICDB01` (database query), `LGSTSQ` (TDQ error logging), `LGCMAREA` copybook, `LGPOLICY` for field definitions, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with code `LGCA` when no commarea provided; returns code `98` for insufficient commarea length; writes timestamped diagnostic entries via `LGSTSQ`.
- Notes: requires commarea length to accommodate both header/trailer (18 bytes) plus customer data structure from `LGPOLICY` copybook.

### LGUCUS01 – Update Customer Transaction  
- Purpose: front-end CICS task for updating customer details; validates request ID and delegates modification to `LGUCDB01`.
- Interfaces: expects `DFHCOMMAREA` shaped by `LGCMAREA` with request ID `01UCUS` and customer update payload; initializes return codes on entry.
- Dependencies: `LGUCDB01` (database update), `LGSTSQ` (TDQ error logging), `LGCMAREA` copybook for shared structures, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with code `LGCA` when no commarea provided; returns code `99` for unrecognized request ID; writes timestamped diagnostic entries via `LGSTSQ`.
- Notes: includes VARCHAR field handling capability with 3900-character variable data support; validates specific request ID before processing.

### LGIPOL01 – Inquire Policy Transaction
- Purpose: front-end CICS task for retrieving policy information; delegates lookup to `LGIPDB01` backend service.
- Interfaces: expects `DFHCOMMAREA` shaped by `LGCMAREA` with policy inquiry payload; initializes `CA-RETURN-CODE` to `00` on entry.
- Dependencies: `LGIPDB01` (database query), `LGSTSQ` (TDQ error logging), `LGCMAREA` copybook, `LGPOLICY` for field definitions, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with code `LGCA` when no commarea provided; writes timestamped diagnostic entries via `LGSTSQ` and preserves commarea contents for debugging.
- Notes: simple front-end that performs minimal validation before delegating all inquiry logic to database backend service.

### LGUPOL01 – Update Policy Transaction
- Purpose: front-end CICS task for updating policy details; validates request type and commarea length before delegating to `LGUPDB01`.
- Interfaces: expects `DFHCOMMAREA` shaped by `LGCMAREA` with update request IDs (`01UEND`, `01UHOU`, `01UMOT`) and corresponding policy data.
- Dependencies: `LGUPDB01` (database update), `LGSTSQ` (TDQ error logging), `LGCMAREA` copybook, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with code `LGCA` when no commarea provided; returns code `98` for insufficient length, `99` for unrecognized request ID; comprehensive error logging.
- Notes: calculates required commarea length based on policy type (Endowment: 124, House: 130, Motor: 137 bytes) plus 28-byte header.

### LGDPOL01 – Delete Policy Transaction
- Purpose: front-end CICS task for deleting policy records; validates request type before delegating deletion to `LGDPDB01`.
- Interfaces: expects `DFHCOMMAREA` shaped by `LGCMAREA` with delete request IDs (`01DEND`, `01DMOT`, `01DHOU`, `01DCOM`) and policy identifier.
- Dependencies: `LGDPDB01` (database deletion), `LGSTSQ` (TDQ error logging), `LGCMAREA` copybook, CICS commands (`LINK`, `RETURN`, `ASKTIME`).
- Error Handling: abends with code `LGCA` when no commarea provided; returns code `98` for insufficient length, `99` for unrecognized request ID; early return on deletion errors.
- Notes: converts request ID to uppercase for validation; supports all four policy types (Endowment, Motor, House, Commercial) for deletion operations.

### LGDPDB01 – Delete Policy Database Service
- Purpose: DB2-backed policy deletion service that removes policy records from the main POLICY table leveraging cascading foreign key relationships.
- Interfaces: requires `LGCMAREA` with customer and policy numbers for targeted deletion; validates specific request IDs (`01DEND`, `01DHOU`, `01DCOM`, `01DMOT`).
- Dependencies: DB2 `POLICY` table (primary), cascaded child tables via foreign keys, `LGDPVS01` (VSAM cleanup), `LGCMAREA` copybook, `LGSTSQ` for error logging.
- Error Handling: returns code `99` for unrecognized request IDs, `90` for SQL errors; logs detailed diagnostic information including customer/policy numbers and SQL codes.
- Notes: performs single DELETE against POLICY table relying on DB2 foreign key constraints to cascade deletion to child policy-type tables; invokes `LGDPVS01` for VSAM synchronization after successful DB2 operation.

### LGIPDB01 – Inquire Policy Database Service
- Purpose: comprehensive policy inquiry service supporting multiple query types (single policy, customer policies, geographic searches) with cursor-based result sets.
- Interfaces: accepts various request IDs (`01IEND`, `01IHOU`, `01IMOT`, `01ICOM`, `02ICOM`, `03ICOM`, `05ICOM`) with corresponding policy type-specific data structures in commarea.
- Dependencies: DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`, `COMMERCIAL`), `LGCMAREA` and `LGPOLICY` copybooks for data mapping, `LGSTSQ` for error logging.
- Error Handling: returns `01` for no records found, `90` for SQL errors, `98` for insufficient commarea length; comprehensive cursor management with cleanup on errors.
- Notes: uses DB2 cursors for multi-row commercial policy searches; handles nullable fields with indicator variables; dynamically calculates required commarea sizes based on variable-length policy data.

### LGICDB01 – Inquire Customer Database Service  
- Purpose: simple customer information retrieval service that queries the CUSTOMER table by customer number and returns complete customer profile.
- Interfaces: expects `LGCMAREA` with customer number; returns full customer details including personal information, address, and contact details.
- Dependencies: DB2 `CUSTOMER` table, `LGCMAREA` and `LGPOLICY` copybooks for field definitions, `LGSTSQ` for error logging.
- Error Handling: returns `01` for customer not found or deadlock conditions (`-913`), `90` for other SQL errors, `98` for insufficient commarea length.
- Notes: straightforward single-row SELECT operation; validates minimum commarea length to accommodate customer data structure; includes comprehensive error logging with SQL diagnostic information.

### LGUCDB01 – Update Customer Database Service
- Purpose: customer information update service that modifies customer profile data in DB2 and synchronizes changes to VSAM via `LGUCVS01`.
- Interfaces: consumes `LGCMAREA` with updated customer details including names, birth date, address, phone numbers, and email address.
- Dependencies: DB2 `CUSTOMER` table, `LGUCVS01` (VSAM synchronization), `LGCMAREA` and `LGPOLICY` copybooks, `LGSTSQ` for error logging.
- Error Handling: returns `01` for customer not found, `90` for SQL errors; logs detailed diagnostic information including customer number and SQL operation results.
- Notes: performs comprehensive customer profile update with nine field modifications; automatically invokes `LGUCVS01` to maintain VSAM file consistency after successful DB2 update.

### LGUPDB01 – Update Policy Database Service
- Purpose: sophisticated policy update service supporting endowment, house, and motor policy modifications with optimistic concurrency control via timestamp validation.
- Interfaces: handles request IDs (`01UEND`, `01UHOU`, `01UMOT`) with corresponding policy-specific data structures; includes broker and payment information updates.
- Dependencies: DB2 tables (`POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`), `LGUPVS01` (VSAM sync), `LGCMAREA` and `LGPOLICY` copybooks, `LGSTSQ` for error logging, DB2 cursors for row locking.
- Error Handling: returns `01` for policy not found, `02` for timestamp mismatch (concurrent update), `90` for SQL errors; includes transaction rollback on failures and comprehensive cursor cleanup.
- Notes: uses DB2 cursor with FOR UPDATE to lock policy records; validates last-changed timestamp to detect concurrent modifications; updates both main POLICY table and policy-type-specific tables; refreshes timestamp and synchronizes to VSAM on successful completion.

## Immediate Findings & Questions
- `install.sh` expects `tsocmd` and USS `cp` with dataset support; confirm environment prerequisites.
- Customer experience assets hint at established monitoring and test flows; identify current owners.
- Need to verify whether source members align with current CICS region configuration.
- Images folder currently holds `initial_topology.jpg`; consider exporting architecture notes from there.

## Workstation Simulator Transaction Scripts
### Customer Transaction Scripts (SSC1*)
#### SSC1A1 - Customer Add Simulation
- Purpose: simulates creation of new customer records through the 3270 interface using transaction `SSC1`.
- Flow: navigates to customer add screen, generates random customer data (names from UTBL tables, birth dates, addresses), submits via PF2, validates success message "New Customer Inserted".
- Data Generation: uses UTBL reference tables (`Fname`, `Sname`, `Pcode`) for realistic test data; generates birth dates between 1940-1980, random addresses and postal codes.
- Error Handling: increments `eCount_lu2_SSC1A1` counter on failure, includes optional email notification when transaction count exceeds `STRT_Stats_Out` threshold.
- Dependencies: `#SSVARS` for shared simulation variables, UTBL reference data tables, transaction `SSC1` (maps to `LGACUS01` COBOL program).

#### SSC1I1 - Customer Inquiry Simulation  
- Purpose: simulates customer information retrieval through transaction `SSC1` inquiry function (option 1).
- Flow: first executes `LGCF` to establish customer context, extracts customer number from screen, then performs inquiry via `SSC1` transaction.
- Interface: positions cursor at row 22, column 25 and types '1' to select inquiry option, validates screen response.
- Error Handling: includes counter `Count_lu2_SSC1I1` for performance tracking, debug logging when `STRT_Debugit = 'ON'`.
- Dependencies: requires active customer session context from `LGCF`, transaction `SSC1` (maps to `LGICUS01` COBOL program).

### Motor Policy Transaction Scripts (SSP1*)
#### SSP1A1 - Motor Policy Add Simulation
- Purpose: simulates motor insurance policy creation through transaction `SSP1` add function.
- Flow: establishes customer context via `LGCF`, extracts customer number, generates comprehensive motor policy data including vehicle details, dates, and premiums.
- Data Generation: creates start/expiry dates (1997-2007), vehicle make/model from UTBL tables (`Cmake`, `Cmodel`), registration numbers, colors (`Ccolor`), values (13000-38000), and manufactured dates (1975-2007).
- Validation: expects success message "New Motor Policy Inserted", logs failure via `eCount_lu2_SSP1A1` counter.
- Dependencies: customer context from `LGCF`, UTBL reference tables for vehicle data, transaction `SSP1` (maps to `LGAPOL01` COBOL program).

#### SSP1I1 - Motor Policy Inquiry Simulation
- Purpose: simulates motor policy information retrieval using policy finder and inquiry functions.
- Flow: uses `LGPF M` command to locate motor policies for customer, extracts policy details from screen, then performs detailed inquiry via `SSP1`.
- Data Extraction: parses screen for policy key format, validates policy type 'M' (Motor), extracts policy and customer numbers for inquiry.
- Error Handling: includes conditional logic to skip inquiry if no motor policy found, tracks performance via `Count_lu2_SSP1I1`.
- Dependencies: `LGPF` policy finder utility, transaction `SSP1` (maps to `LGIPOL01` COBOL program).

#### SSP1U1 - Motor Policy Update Simulation
- Purpose: simulates modification of existing motor policy details through transaction `SSP1` update function (option 4).
- Flow: locates existing motor policy via `LGPF M`, validates "No data" condition, generates updated policy information, submits changes.
- Data Updates: modifies policy dates, vehicle make/model, value, registration, color, premium amounts using randomized data within realistic ranges.
- Validation: expects "Motor Policy Updated" success message, handles update failures via `eCount_lu2_SSP1U1` error counter.
- Dependencies: existing motor policy records, UTBL reference tables, transaction `SSP1` (maps to `LGUPOL01` COBOL program).

#### SSP1D1 - Motor Policy Delete Simulation  
- Purpose: simulates deletion of motor insurance policies through transaction `SSP1` delete function (option 3).
- Flow: uses policy finder to locate motor policy, extracts policy identifiers, performs deletion via option 3.
- Validation: expects "Motor Policy Deleted" confirmation message, logs deletion failures via `eCount_lu2_SSP1D1`.
- Dependencies: existing policy records, `LGPF` policy finder, transaction `SSP1` (maps to `LGDPOL01` COBOL program).

### Endowment/Life Policy Transaction Scripts (SSP2*)
#### SSP2A1 - Endowment Policy Add Simulation
- Purpose: simulates life insurance policy creation through transaction `SSP2` add function.
- Flow: establishes customer context, generates endowment policy data including beneficiary information, coverage amounts, and policy terms.
- Data Generation: creates policy dates (1997-2007), coverage amounts (10000-999000), beneficiary names from UTBL tables, random Y/N flags for policy options.
- Validation: expects "New Life Policy Inserted" success message, tracks failures via `eCount_lu2_SSP2A1`.
- Dependencies: customer context, UTBL name tables (`Fname`, `Sname`), transaction `SSP2` (maps to `LGAPOL01` COBOL program).

#### SSP2U1 - Endowment Policy Update Simulation
- Purpose: simulates updates to existing endowment policy details.
- Flow: locates endowment policy via `LGPF E`, generates updated beneficiary and coverage information, submits via update option.
- Data Updates: modifies beneficiary names, coverage amounts, policy flags (withholding tax, medical details, etc.) using random data.
- Dependencies: existing endowment policies, transaction `SSP2` (maps to `LGUPOL01` COBOL program).

#### SSP2I1 - Endowment Policy Inquiry Simulation
- Purpose: retrieves endowment policy details through inquiry function.
- Dependencies: `LGPF` policy finder, transaction `SSP2` (maps to `LGIPOL01` COBOL program).

#### SSP2D1 - Endowment Policy Delete Simulation
- Purpose: deletes endowment policies through delete function.
- Dependencies: existing policy records, transaction `SSP2` (maps to `LGDPOL01` COBOL program).

### House Policy Transaction Scripts (SSP3*)
#### SSP3A1 - House Policy Add Simulation
- Purpose: simulates house insurance policy creation through transaction `SSP3`.
- Flow: establishes customer context, generates house policy data including property details, coverage types, and premiums.
- Data Generation: creates policy dates, house types from UTBL (`Htype`), property values (100000-999000), address information, postal codes from UTBL (`Pcode`).
- Validation: expects "New House Policy Inserted" confirmation message.
- Dependencies: customer context, UTBL reference tables for house data, transaction `SSP3` (maps to `LGAPOL01` COBOL program).

#### SSP3U1 - House Policy Update Simulation  
- Purpose: simulates updates to existing house policy details.
- Flow: locates house policy via `LGPF H`, generates updated property and coverage information.
- Dependencies: existing house policies, transaction `SSP3` (maps to `LGUPOL01` COBOL program).  

#### SSP3I1 - House Policy Inquiry Simulation
- Purpose: retrieves house policy information through inquiry function.
- Dependencies: `LGPF` policy finder, transaction `SSP3` (maps to `LGIPOL01` COBOL program).

#### SSP3D1 - House Policy Delete Simulation
- Purpose: deletes house insurance policies.
- Validation: expects "House Policy Deleted" confirmation message.
- Dependencies: existing policy records, transaction `SSP3` (maps to `LGDPOL01` COBOL program).

### Commercial Policy Transaction Scripts (SSP4*)  
#### SSP4A1 - Commercial Policy Add Simulation
- Purpose: simulates commercial property insurance policy creation through transaction `SSP4`.
- Flow: generates comprehensive commercial property data including location coordinates, peril coverages, and premium calculations.
- Data Generation: creates property addresses, postal codes, latitude/longitude coordinates, customer names, property types from UTBL (`Ptype`), and detailed peril coverages (Fire, Crime, Flood, Weather) with corresponding premiums.
- Validation: expects "New Commercial Policy Inserted" success message.
- Dependencies: extensive UTBL reference tables, transaction `SSP4` (maps to `LGAPOL01` COBOL program).

#### SSP4I1 - Commercial Policy Inquiry Simulation
- Purpose: retrieves commercial policy details through inquiry function.
- Dependencies: `LGPF` policy finder, transaction `SSP4` (maps to `LGIPOL01` COBOL program).

#### SSP4D1 - Commercial Policy Delete Simulation  
- Purpose: deletes commercial property policies.
- Validation: expects "Commercial Policy Deleted" confirmation message.
- Dependencies: existing policy records, transaction `SSP4` (maps to `LGDPOL01` COBOL program).

### Data Generation Modules (A2 Scripts)
- **SSC1A2**: customer data generation module providing variables (VS1-VS6) for names, birth dates, addresses, and postal codes used by customer add simulations.
- **SSP1A2**: motor policy data generation module providing variables (VS1-VS10) for customer numbers, policy dates, vehicle details (make/model/color), values, and registration information.
- **SSP2A2**: endowment policy data generation module providing variables for beneficiary names, coverage amounts, policy terms, and flags.
- **SSP3A2**: house policy data generation module providing variables for property details, house types, values, and location information.

### Simulation Script Architecture
- **Variable Sharing**: all scripts include `#SSVARS` for shared simulation state, counters, and configuration.
- **Data Generation**: extensive use of UTBL reference tables for realistic test data (names, codes, types) and A2 modules for structured variable sets.
- **Error Tracking**: consistent error counter naming (`eCount_lu2_*`) and optional email notification system.
- **Debug Support**: conditional debug logging when `STRT_Debugit = 'ON'`, performance statistics when `STRT_Debugit = 'TEST'`.
- **Screen Automation**: 3270 terminal automation using cursor positioning, field typing, function key transmission, and screen validation.
- **Transaction Integration**: each script maps to corresponding CICS transactions and COBOL programs in the GenApp system.
- **Modular Design**: A1 scripts handle transaction flow and screen interaction, A2 modules provide reusable data generation logic.

## Next Steps
- Inventory high-priority COBOL transactions first (e.g., customer inquiry vs policy update paths).
- Decide documentation template for program deep-dives; store drafts alongside `AGENTS.md` notes.
- Align with operations to validate JCL sequencing before running in target environment.
- Capture modernization goals (e.g., API enablement, refactoring) once stakeholder input arrives.
