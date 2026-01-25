-- Reset PostgreSQL sequences after CSV import
-- This script ensures that auto-increment sequences are aligned with the actual max IDs in tables
-- Run this after importing data from CSV files with explicit IDs

-- Reset agent sequence
SELECT setval('public.thoth_core_agent_id_seq', 
              COALESCE((SELECT MAX(id) FROM public.thoth_core_agent), 1), 
              true);

-- Reset aimodel sequence
SELECT setval('public.thoth_core_aimodel_id_seq', 
              COALESCE((SELECT MAX(id) FROM public.thoth_core_aimodel), 1), 
              true);

-- Reset setting sequence
SELECT setval('public.thoth_core_setting_id_seq', 
              COALESCE((SELECT MAX(id) FROM public.thoth_core_setting), 1), 
              true);

-- Reset workspace sequence
SELECT setval('public.thoth_core_workspace_id_seq', 
              COALESCE((SELECT MAX(id) FROM public.thoth_core_workspace), 1), 
              true);

-- Display results for verification
SELECT 
    'thoth_core_agent' as table_name,
    (SELECT MAX(id) FROM public.thoth_core_agent) as max_id,
    (SELECT last_value FROM public.thoth_core_agent_id_seq) as seq_value
UNION ALL
SELECT 
    'thoth_core_aimodel' as table_name,
    (SELECT MAX(id) FROM public.thoth_core_aimodel) as max_id,
    (SELECT last_value FROM public.thoth_core_aimodel_id_seq) as seq_value
UNION ALL
SELECT 
    'thoth_core_setting' as table_name,
    (SELECT MAX(id) FROM public.thoth_core_setting) as max_id,
    (SELECT last_value FROM public.thoth_core_setting_id_seq) as seq_value
UNION ALL
SELECT 
    'thoth_core_workspace' as table_name,
    (SELECT MAX(id) FROM public.thoth_core_workspace) as max_id,
    (SELECT last_value FROM public.thoth_core_workspace_id_seq) as seq_value
ORDER BY table_name;
