# Enhanced SQL Generation Workflow Documentation

## Overview
This document describes the enhanced SQL generation and evaluation workflow implemented in ThothAI, featuring multi-agent orchestration with semantic test deduplication and intelligent SQL selection.

## Source Files Involved

### Main Orchestration
- **`frontend/sql_generator/main.py`**
  - Entry point for FastAPI application
  - Coordinates the entire SQL generation pipeline
  - Handles streaming responses to client

### Workflow Phases
- **`frontend/sql_generator/helpers/main_helpers/main_request_initialization.py`**
  - Initializes request state and validation
  
- **`frontend/sql_generator/helpers/main_helpers/main_preprocessing_phases.py`**
  - Phase 1: Question validation
  - Phase 2: Keyword extraction  
  - Phase 3: Context retrieval

- **`frontend/sql_generator/helpers/main_helpers/main_generation_phases.py`**
  - Phase 4: SQL generation orchestration
  - Phase 5: Evaluation and selection coordination
  - Integrates enhanced evaluation flow

- **`frontend/sql_generator/helpers/main_helpers/main_response_preparation.py`**
  - Phase 6: Final response preparation
  - Workspace state management

### Enhanced Evaluation System
- **`frontend/sql_generator/helpers/main_helpers/enhanced_evaluation_flow.py`**
  - Core enhanced evaluation logic
  - 4-case decision system (A, B, C, D)
  - Auxiliary agent coordination

- **`frontend/sql_generator/helpers/main_helpers/main_evaluation.py`**
  - Test deduplication (exact matching)
  - Test semantic filtering integration
  - Standard evaluation execution

### Agent Components
- **`frontend/sql_generator/agents/test_reducer_agent.py`**
  - Semantic test deduplication
  - Similarity analysis and filtering

- **`frontend/sql_generator/agents/sql_selector_agent.py`**
  - Selects best SQL from multiple 100% candidates
  - Quality and efficiency analysis

- **`frontend/sql_generator/agents/evaluator_supervisor_agent.py`**
  - Reviews borderline SQL evaluations
  - Deep analysis for threshold cases

- **`frontend/sql_generator/agents/core/agent_manager.py`**
  - Agent pool management
  - Model configuration and initialization

### Supporting Components
- **`frontend/sql_generator/model/system_state.py`**
  - System state management
  - Workflow data persistence

- **`frontend/sql_generator/agents/core/agent_result_models.py`**
  - Enhanced evaluation result models
  - Status enumerations

- **`frontend/sql_generator/helpers/main_helpers/evaluation_logger.py`**
  - Detailed evaluation logging
  - Performance metrics tracking

## Workflow Diagram

```mermaid
flowchart TD
    Start([User Question]) --> Init[Initialize Request State]
    Init --> Phase1[Phase 1: Validate Question]
    Phase1 --> Phase2[Phase 2: Extract Keywords]
    Phase2 --> Phase3[Phase 3: Retrieve Context<br/>Schema, Examples, Evidence]
    Phase3 --> Phase4[Phase 4: Generate SQL Candidates<br/>Parallel Generation]
    
    Phase4 --> Dedup[Deduplicate Tests<br/>Remove Identical]
    Dedup --> TestReduce{Tests > 5?}
    TestReduce -->|Yes| Semantic[TestReducer Agent<br/>Remove Similar Tests]
    TestReduce -->|No| Eval[Standard Evaluation]
    Semantic --> Eval
    
    Eval --> CalcRates[Calculate Pass Rates<br/>OK/KO per SQL]
    CalcRates --> Classify[Classify Case]
    
    Classify --> CaseA{Case A?<br/>Single 100%}
    Classify --> CaseB{Case B?<br/>Multiple 100%}
    Classify --> CaseC{Case C?<br/>Borderline<br/>threshold%-99%}
    Classify --> CaseD{Case D?<br/>All < threshold%}
    
    CaseA -->|Yes| Gold1[Select as GOLD]
    CaseB -->|Yes| Selector[SqlSelector Agent<br/>Choose Best]
    CaseC -->|Yes| Supervisor[EvaluatorSupervisor Agent<br/>Deep Review]
    CaseD -->|Yes| Escalate[Escalate to Next Level]
    
    Selector --> Gold2[Select as GOLD]
    Supervisor --> SuperDecision{Approve?}
    SuperDecision -->|Yes| Gold3[Select as GOLD]
    SuperDecision -->|No| Failed[Mark as FAILED]
    
    Gold1 --> Phase6[Phase 6: Prepare Response]
    Gold2 --> Phase6
    Gold3 --> Phase6
    Failed --> Phase6
    Escalate --> Phase6
    
    Phase6 --> End([Return Result])
    
    style CaseA fill:#90EE90
    style CaseB fill:#87CEEB
    style CaseC fill:#FFD700
    style CaseD fill:#FFB6C1
    style Gold1 fill:#32CD32
    style Gold2 fill:#32CD32
    style Gold3 fill:#32CD32
    style Failed fill:#FF6347
    style Escalate fill:#FFA500
```

## Agent Collaboration Diagram

```mermaid
graph TB
    subgraph Core Agents
        Gen[SQL Generator Agent]
        TestGen[Test Generator Agent]
        Eval[Evaluator Agent]
    end
    
    subgraph Auxiliary Agents
        TestRed[TestReducer Agent<br/>Semantic Dedup]
        SqlSel[SqlSelector Agent<br/>Best SQL Choice]
        EvalSup[EvaluatorSupervisor Agent<br/>Borderline Review]
    end
    
    subgraph System Components
        State[System State]
        Logger[Evaluation Logger]
        Manager[Agent Manager]
    end
    
    Gen -->|Generates SQLs| State
    TestGen -->|Generates Tests| State
    State -->|Unique Tests| TestRed
    TestRed -->|Filtered Tests| Eval
    Eval -->|OK/KO Results| State
    
    State -->|Case B: Multiple 100%| SqlSel
    SqlSel -->|Best SQL| State
    
    State -->|Case C: Borderline| EvalSup
    EvalSup -->|Final Decision| State
    
    Manager -.->|Manages| Gen
    Manager -.->|Manages| TestGen
    Manager -.->|Manages| Eval
    Manager -.->|Creates| TestRed
    Manager -.->|Creates| SqlSel
    Manager -.->|Creates| EvalSup
    
    Logger -.->|Logs| TestRed
    Logger -.->|Logs| Eval
    Logger -.->|Logs| SqlSel
    Logger -.->|Logs| EvalSup
    
    style TestRed fill:#E6E6FA
    style SqlSel fill:#E0FFFF
    style EvalSup fill:#FFEFD5
```

## Activity Diagram

```mermaid
stateDiagram-v2
    [*] --> RequestReceived
    
    RequestReceived --> Validation: Initialize State
    
    state Validation {
        [*] --> ValidateQuestion
        ValidateQuestion --> ExtractKeywords
        ExtractKeywords --> RetrieveContext
        RetrieveContext --> [*]
    }
    
    Validation --> SQLGeneration: Context Ready
    
    state SQLGeneration {
        [*] --> GenerateParallel
        GenerateParallel --> CollectSQLs
        CollectSQLs --> GenerateTests
        GenerateTests --> [*]
    }
    
    SQLGeneration --> TestProcessing: SQLs & Tests Ready
    
    state TestProcessing {
        [*] --> DeduplicateExact
        DeduplicateExact --> CheckTestCount
        CheckTestCount --> SemanticFilter: >5 tests
        CheckTestCount --> RunEvaluation: ≤5 tests
        SemanticFilter --> RunEvaluation
        RunEvaluation --> CalculateRates
        CalculateRates --> [*]
    }
    
    TestProcessing --> CaseClassification: Pass Rates Calculated
    
    state CaseClassification {
        [*] --> AnalyzeRates
        AnalyzeRates --> CaseA: Single 100%
        AnalyzeRates --> CaseB: Multiple 100%
        AnalyzeRates --> CaseC: Borderline (threshold%-99%)
        AnalyzeRates --> CaseD: All < threshold%
        
        CaseA --> SelectDirect: GOLD
        CaseB --> RunSelector
        CaseC --> RunSupervisor
        CaseD --> PrepareEscalation
        
        RunSelector --> SelectBest: GOLD
        RunSupervisor --> ReviewDecision
        ReviewDecision --> ApproveSQL: Approved
        ReviewDecision --> RejectSQL: Rejected
        
        SelectDirect --> [*]
        SelectBest --> [*]
        ApproveSQL --> [*]
        RejectSQL --> [*]
        PrepareEscalation --> [*]
    }
    
    CaseClassification --> ResponsePrep: Decision Made
    
    state ResponsePrep {
        [*] --> FormatResponse
        FormatResponse --> SaveState
        SaveState --> StreamToClient
        StreamToClient --> [*]
    }
    
    ResponsePrep --> [*]: Complete
```

## Key Features

### 1. Intelligent Test Management
- **Exact Deduplication**: Removes identical test cases
- **Semantic Filtering**: TestReducer eliminates similar tests while maintaining coverage
- **Dynamic Threshold**: Only applies semantic filtering when >5 tests

### 2. Multi-Case Evaluation System
- **Case A**: Direct selection for single perfect SQL
- **Case B**: SqlSelector for choosing among multiple perfect SQLs
- **Case C**: EvaluatorSupervisor for borderline cases
- **Case D**: Escalation mechanism for all failures

### 3. Threshold-Based Decision Making
- Configurable evaluation threshold (default 90%)
- Borderline zone between threshold and 99%
- Automatic escalation below threshold

### 4. Agent Orchestration
- Core agents handle primary workflow
- Auxiliary agents created on-demand
- Shared model configuration across agents
- Comprehensive logging and metrics

## Configuration

### Evaluation Threshold
Set in workspace configuration:
```python
workspace['evaluation_threshold'] = 90  # 90% minimum pass rate
```

### Agent Model Configuration
Auxiliary agents inherit configuration from the evaluator agent to ensure consistency.

## Performance Considerations

1. **Parallel SQL Generation**: Multiple SQLs generated concurrently
2. **Lazy Agent Creation**: Auxiliary agents created only when needed
3. **Smart Test Filtering**: Reduces evaluation overhead
4. **Streaming Response**: Results streamed to client as available

## Error Handling

- Graceful degradation if auxiliary agents fail
- Fallback to simpler cases when advanced features unavailable
- Comprehensive error logging and context preservation
- Escalation path for systematic failures