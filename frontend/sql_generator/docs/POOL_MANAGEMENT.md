# Agent Pool Management System

## Overview

The Agent Pool Management System is a dynamic, level-based architecture for managing AI agents in the Thoth SQL generation system. This new system replaces the rigid workspace-specific agent assignment with a flexible pool-based approach that allows multiple agents per level and better resource utilization.

## Architecture

### Previous System (Legacy)
- **Fixed Assignment**: Each workspace had specific agents assigned (sql_basic_agent, sql_advanced_agent, sql_expert_agent)
- **Limited Scalability**: Only one agent per level
- **Tight Coupling**: Agents were hardcoded to workspace configuration
- **No Load Balancing**: Single agent handled all requests for its level

### New System (Pool-Based)
- **Dynamic Pools**: Agents are organized by type and level in pools
- **Multiple Agents**: Support for multiple agents per level
- **Loose Coupling**: Agents are classified by their type, not workspace assignment
- **Load Balancing**: Round-robin distribution across available agents

## Components

### 1. Django Backend API

#### Endpoint
```
GET /api/workspace/{workspace_id}/agent-pools/
```

#### Response Structure
```json
{
  "sql_generators": {
    "basic": [
      {
        "id": 1,
        "name": "SQL Basic Agent 1",
        "agent_type": "SQLBASIC",
        "temperature": 0.8,
        "top_p": 0.95,
        "max_tokens": 1280,
        "timeout": 45.0,
        "retries": 5,
        "ai_model": {
          "id": 1,
          "name": "GPT-4",
          "specific_model": "gpt-4-turbo",
          "llm_type": "OPENAI",
          "context_size": 128000
        }
      }
    ],
    "advanced": [...],
    "expert": [...]
  },
  "test_generators": {
    "basic": [...],
    "advanced": [...],
    "expert": [...]
  }
}
```

### 2. Agent Pool Configuration Model

**File**: `sql_generator/model/agent_pool_config.py`

Key Classes:
- `AgentConfig`: Configuration for a single agent
- `LevelPools`: Pools organized by level (basic, advanced, expert)
- `AgentPoolConfig`: Complete pool configuration with helper methods

### 3. AgentPools Class

**File**: `sql_generator/agents/core/agent_pools.py`

Features:
- **Level-based pools**: Separate pools for basic, advanced, and expert levels
- **Legacy compatibility**: Maintains backward compatibility with old system
- **Selection methods**: Random selection, index-based selection, round-robin
- **Statistics**: Pool usage statistics and monitoring

### 4. ThothAgentManager

**File**: `sql_generator/agents/core/agent_manager.py`

Enhancements:
- **Dynamic initialization**: Creates agents from pool configuration
- **Fallback mechanism**: Falls back to legacy pools if configuration unavailable
- **Pool population**: Populates pools based on agent classification

## Agent Classification

Agents are classified using the `AgentChoices` enum in Django models:

### SQL Generators
- `SQLBASIC`: SQL Generator - Basic
- `SQLADVANCED`: SQL Generator - Advanced
- `SQLEXPERT`: SQL Generator - Expert

### Test Generators
- `TESTGENERATORBASIC`: Test Generator - Basic
- `TESTGENERATORADVANCED`: Test Generator - Advanced
- `TESTGENERATOREXPERT`: Test Generator - Expert

## Usage Flow

### 1. Initialization
```python
# Fetch workspace configuration
workspace_config = await _get_workspace(workspace_id)

# Fetch agent pool configuration
agent_pool_config = await _get_agent_pools(workspace_id)

# Initialize agent manager with pool config
agent_manager = ThothAgentManager(workspace_config, dbmanager, agent_pool_config).initialize()
```

### 2. SQL Generation
```python
# Get agents from level-specific pool
level_agents = agent_pools.get_sql_agents_by_level("basic")

# Use round-robin for distribution
for i in range(num_generations):
    agent = level_agents[i % len(level_agents)]
    # Generate SQL with agent
```

### 3. Test Generation
```python
# Get test agents by level
test_agents = agent_pools.get_test_agents_by_level("advanced")

# Distribute work across agents
for i, test in enumerate(tests):
    agent = test_agents[i % len(test_agents)]
    # Generate test with agent
```

## Benefits

### 1. Flexibility
- Add or remove agents without code changes
- Agents can be shared across workspaces
- Easy to scale up or down based on load

### 2. Performance
- Parallel execution with multiple agents
- Load balancing across available resources
- Better resource utilization

### 3. Maintainability
- Centralized agent management in Django admin
- Clear separation of concerns
- Easier debugging and monitoring

### 4. Scalability
- Support for multiple agents per level
- Easy to add new agent types
- Cloud-ready architecture

## Migration from Legacy System

The system maintains backward compatibility:

1. **Automatic Fallback**: If pool configuration is not available, system falls back to legacy workspace-specific agents
2. **Dual Support**: Both pool-based and legacy methods work simultaneously
3. **Gradual Migration**: Workspaces can be migrated one at a time

## Configuration

### Django Admin Setup

1. Create agents with appropriate classifications:
   - Set `agent_type` to appropriate value (e.g., `SQLBASIC`, `TESTGENERATORADVANCED`)
   - Configure AI model and parameters
   - Agents are automatically included in pools based on their type

2. Workspace configuration remains unchanged:
   - Legacy workspace agents still work
   - Pool-based agents supplement or replace them

### Environment Variables

```bash
# Django backend connection
DJANGO_SERVER=http://localhost:8040
DJANGO_API_KEY=your-api-key-here
```

## Monitoring and Debugging

### Pool Statistics
```python
stats = agent_pools.get_pool_stats()
# Returns:
# {
#   'sql': {
#     'basic': 3,
#     'advanced': 2,
#     'expert': 1,
#     'total': 6
#   },
#   'test': {...}
# }
```

### Logging
The system logs:
- Agent pool fetching from Django
- Agent selection for each generation
- Pool statistics after initialization
- Fallback to legacy when pools unavailable

## Dynamic MSchema Construction

### Overview

The system now implements dynamic, on-the-fly construction of the `used_mschema` for Test Generator and SQL Generator agents. This enhancement improves agent diversity and reduces overfitting by providing slightly different schema representations for each agent run.

### Key Changes

#### Previous Approach (Static)
- A single `state.used_mschema` was generated once and reused across all agent runs
- All agents received identical schema representations
- Limited diversity in agent responses

#### New Approach (Dynamic)
- MSchema is generated on-the-fly for each agent run
- Schema construction varies based on `schema_linking_strategy`
- Tables and columns are shuffled before transformation to introduce variability
- Each agent run receives a unique schema representation

### Implementation Details

#### Schema Construction Strategy

1. **WITHOUT_SCHEMA_LINK Strategy**:
   - Uses the complete database schema
   - Applies shuffling to all tables and columns
   - Transforms to mschema format via `to_mschema()` function

2. **Other Strategies** (WITH_SCHEMA_LINK, etc.):
   - Uses filtered schema based on relevance
   - Applies shuffling to filtered tables and columns
   - Transforms to mschema format via `to_mschema()` function

#### Workflow

```python
# For each agent run:
def generate_dynamic_mschema(schema, strategy):
    if strategy == "WITHOUT_SCHEMA_LINK":
        working_schema = complete_schema
    else:
        working_schema = filtered_schema
    
    # Shuffle for variability
    shuffled_schema = shuffle_tables_and_columns(working_schema)
    
    # Transform to mschema format
    dynamic_mschema = to_mschema(shuffled_schema)
    
    return dynamic_mschema
```

#### Key Characteristics

1. **Ephemeral Nature**: MSchemas are created per-run and not stored in state
2. **Variability**: Shuffling ensures each agent sees a slightly different schema order
3. **Strategy-Aware**: Schema content adapts to the linking strategy
4. **Documentation Purpose**: The original `state.mschema` is retained for documentation but not used in generation

### Benefits

1. **Improved Diversity**: Each agent run produces more varied outputs
2. **Reduced Overfitting**: Agents don't memorize fixed schema orderings
3. **Better Generalization**: Agents learn to work with varying schema presentations
4. **Strategy Optimization**: Schema content is optimized per linking strategy

### Integration with Agent Pools

The dynamic mschema construction works seamlessly with the pool management system:

1. **Per-Agent Variation**: Each agent in a pool receives a unique schema representation
2. **Parallel Execution**: Multiple agents can work with different schema views simultaneously
3. **Load Balancing**: Schema shuffling adds minimal overhead to agent selection

### Example Usage

```python
# In main_sql_generation.py or main_test_generation.py
async def generate_with_agent(agent, state, strategy):
    # Generate dynamic mschema for this specific run
    if strategy == "WITHOUT_SCHEMA_LINK":
        base_schema = state.complete_schema
    else:
        base_schema = state.filtered_schema
    
    # Shuffle and transform
    shuffled_schema = shuffle_schema_elements(base_schema)
    dynamic_mschema = to_mschema(shuffled_schema)
    
    # Use in prompt (not stored in state)
    prompt = build_prompt(
        question=state.question,
        mschema=dynamic_mschema,  # Dynamic, not state.used_mschema
        ...
    )
    
    result = await agent.generate(prompt)
    return result
```

### Important Notes

1. **No State Storage**: Dynamic mschemas are never stored in `state`
2. **Generation-Time Creation**: MSchemas are created at prompt generation time
3. **Independent Runs**: Each agent run is independent with its own schema view
4. **Backward Compatibility**: The original `state.mschema` remains for documentation purposes

## Future Enhancements

1. **Dynamic Agent Scaling**: Auto-scale agents based on load
2. **Agent Health Monitoring**: Track agent performance and errors
3. **Weighted Selection**: Prefer high-performing agents
4. **Agent Specialization**: Agents specialized for specific SQL patterns
5. **A/B Testing**: Compare agent performance for optimization
6. **Cost Optimization**: Select agents based on cost/performance ratio
7. **Adaptive Schema Shuffling**: Adjust shuffling strategy based on query complexity
8. **Schema Caching**: Cache frequently used schema patterns for performance

## Troubleshooting

### No Agents in Pool
- Check Django admin for agents with correct `agent_type`
- Verify API endpoint is accessible
- Check DJANGO_API_KEY is set correctly

### Fallback to Legacy
- Check logs for pool fetch errors
- Verify workspace has access permissions
- Ensure Django backend is running

### Performance Issues
- Monitor pool statistics for imbalanced distribution
- Check agent timeout settings
- Verify parallel execution is working

## Code Examples

### Creating Custom Pool Selection Strategy
```python
class CustomPoolStrategy:
    def select_agent(self, agents, context):
        # Custom selection logic
        if context.complexity > 0.8:
            # Prefer agents with higher temperature
            return max(agents, key=lambda a: a.temperature)
        else:
            # Random selection for simple queries
            return random.choice(agents)
```

### Adding New Agent Type
```python
# In Django models.py
class AgentChoices(models.TextChoices):
    # ... existing choices ...
    SQLULTRA = 'SQLULTRA', 'SQL Generator - Ultra'

# In agent_pools.py
self.sql_pools['ultra'] = []

# Classification logic
if agent.agent_type == AgentChoices.SQLULTRA:
    result["sql_generators"]["ultra"].append(agent_data)
```

## Summary

The Agent Pool Management System provides a robust, scalable solution for managing AI agents in Thoth. By moving from fixed agent assignments to dynamic pools, the system achieves better resource utilization, improved performance, and easier maintenance while maintaining full backward compatibility.