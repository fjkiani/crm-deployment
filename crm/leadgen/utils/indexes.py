"""
Database Indexes for Lead Generation System
Optimizes query performance for common operations
"""

import frappe

def create_leadgen_indexes():
    """Create database indexes for lead generation tables"""
    
    indexes = [
        # Lead Prospect indexes
        {
            "table": "tabLead Prospect",
            "columns": ["tier", "lead_score"],
            "name": "idx_lead_prospect_tier_score"
        },
        {
            "table": "tabLead Prospect", 
            "columns": ["source", "source_ref_id"],
            "name": "idx_lead_prospect_source"
        },
        {
            "table": "tabLead Prospect",
            "columns": ["outreach_status", "last_contacted"],
            "name": "idx_lead_prospect_outreach"
        },
        {
            "table": "tabLead Prospect",
            "columns": ["pi_email"],
            "name": "idx_lead_prospect_email"
        },
        {
            "table": "tabLead Prospect",
            "columns": ["institution"],
            "name": "idx_lead_prospect_institution"
        },
        {
            "table": "tabLead Prospect",
            "columns": ["owner", "tier"],
            "name": "idx_lead_prospect_owner_tier"
        },
        
        # LeadGen Job indexes
        {
            "table": "tabLeadGen Job",
            "columns": ["job_type", "status"],
            "name": "idx_leadgen_job_type_status"
        },
        {
            "table": "tabLeadGen Job",
            "columns": ["owner", "status"],
            "name": "idx_leadgen_job_owner_status"
        },
        {
            "table": "tabLeadGen Job",
            "columns": ["created", "status"],
            "name": "idx_leadgen_job_created_status"
        },
        
        # Lead Prospect Match indexes
        {
            "table": "tabLead Prospect Match",
            "columns": ["prospect_1", "prospect_2"],
            "name": "idx_lead_prospect_match_prospects"
        },
        {
            "table": "tabLead Prospect Match",
            "columns": ["status", "confidence_score"],
            "name": "idx_lead_prospect_match_status_score"
        },
        
        # Outreach Sequence Instance indexes
        {
            "table": "tabOutreach Sequence Instance",
            "columns": ["prospect", "outreach_sequence"],
            "name": "idx_outreach_instance_prospect_sequence"
        },
        {
            "table": "tabOutreach Sequence Instance",
            "columns": ["status", "next_send_date"],
            "name": "idx_outreach_instance_status_send_date"
        },
        {
            "table": "tabOutreach Sequence Instance",
            "columns": ["outreach_sequence", "status"],
            "name": "idx_outreach_instance_sequence_status"
        },
        
        # CRM Lead custom fields indexes
        {
            "table": "tabCRM Lead",
            "columns": ["tier", "lead_score"],
            "name": "idx_crm_lead_tier_score"
        },
        {
            "table": "tabCRM Lead",
            "columns": ["prospect_ref"],
            "name": "idx_crm_lead_prospect_ref"
        }
    ]
    
    for index in indexes:
        try:
            frappe.db.sql(f"""
                CREATE INDEX IF NOT EXISTS {index['name']} 
                ON {index['table']} ({', '.join(index['columns'])})
            """)
            frappe.logger("leadgen_indexes").info(f"Created index {index['name']}")
        except Exception as e:
            frappe.log_error(f"Failed to create index {index['name']}: {str(e)}")

def drop_leadgen_indexes():
    """Drop lead generation indexes"""
    
    index_names = [
        "idx_lead_prospect_tier_score",
        "idx_lead_prospect_source", 
        "idx_lead_prospect_outreach",
        "idx_lead_prospect_email",
        "idx_lead_prospect_institution",
        "idx_lead_prospect_owner_tier",
        "idx_leadgen_job_type_status",
        "idx_leadgen_job_owner_status",
        "idx_leadgen_job_created_status",
        "idx_lead_prospect_match_prospects",
        "idx_lead_prospect_match_status_score",
        "idx_outreach_instance_prospect_sequence",
        "idx_outreach_instance_status_send_date",
        "idx_outreach_instance_sequence_status",
        "idx_crm_lead_tier_score",
        "idx_crm_lead_prospect_ref"
    ]
    
    for index_name in index_names:
        try:
            frappe.db.sql(f"DROP INDEX IF EXISTS {index_name}")
            frappe.logger("leadgen_indexes").info(f"Dropped index {index_name}")
        except Exception as e:
            frappe.log_error(f"Failed to drop index {index_name}: {str(e)}")

def analyze_table_performance():
    """Analyze table performance and suggest optimizations"""
    
    tables = [
        "tabLead Prospect",
        "tabLeadGen Job", 
        "tabLead Prospect Match",
        "tabOutreach Sequence Instance",
        "tabOutreach Sequence"
    ]
    
    performance_report = {}
    
    for table in tables:
        try:
            # Get table size
            size_result = frappe.db.sql(f"""
                SELECT 
                    table_name,
                    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size in MB'
                FROM information_schema.TABLES 
                WHERE table_schema = DATABASE() 
                AND table_name = '{table.replace('tab', '')}'
            """, as_dict=True)
            
            # Get row count
            count_result = frappe.db.sql(f"SELECT COUNT(*) as count FROM {table}", as_dict=True)
            
            # Get index usage
            index_result = frappe.db.sql(f"""
                SELECT 
                    INDEX_NAME,
                    CARDINALITY
                FROM information_schema.STATISTICS 
                WHERE table_schema = DATABASE() 
                AND table_name = '{table.replace('tab', '')}'
                ORDER BY CARDINALITY DESC
            """, as_dict=True)
            
            performance_report[table] = {
                "size_mb": size_result[0]["Size in MB"] if size_result else 0,
                "row_count": count_result[0]["count"] if count_result else 0,
                "indexes": index_result
            }
            
        except Exception as e:
            frappe.log_error(f"Failed to analyze {table}: {str(e)}")
            performance_report[table] = {"error": str(e)}
    
    return performance_report

def optimize_queries():
    """Optimize common queries with query hints and suggestions"""
    
    optimizations = [
        {
            "query": "SELECT * FROM `tabLead Prospect` WHERE tier = 'Tier 1' ORDER BY lead_score DESC",
            "optimization": "Use index idx_lead_prospect_tier_score",
            "suggestion": "Query is already optimized with proper index"
        },
        {
            "query": "SELECT * FROM `tabLeadGen Job` WHERE job_type = 'clinicaltrials' AND status = 'Running'",
            "optimization": "Use index idx_leadgen_job_type_status", 
            "suggestion": "Query is already optimized with proper index"
        },
        {
            "query": "SELECT * FROM `tabLead Prospect` WHERE pi_email = 'email@example.com'",
            "optimization": "Use index idx_lead_prospect_email",
            "suggestion": "Query is already optimized with proper index"
        },
        {
            "query": "SELECT * FROM `tabOutreach Sequence Instance` WHERE next_send_date <= NOW() AND status = 'In Progress'",
            "optimization": "Use index idx_outreach_instance_status_send_date",
            "suggestion": "Query is already optimized with proper index"
        }
    ]
    
    return optimizations

def get_query_performance_stats():
    """Get query performance statistics"""
    
    try:
        # Get slow query log
        slow_queries = frappe.db.sql("""
            SELECT 
                query_time,
                lock_time,
                rows_sent,
                rows_examined,
                sql_text
            FROM mysql.slow_log 
            WHERE start_time >= DATE_SUB(NOW(), INTERVAL 1 DAY)
            ORDER BY query_time DESC
            LIMIT 10
        """, as_dict=True)
        
        # Get table access patterns
        table_access = frappe.db.sql("""
            SELECT 
                table_name,
                COUNT(*) as access_count
            FROM information_schema.processlist 
            WHERE command = 'Query'
            GROUP BY table_name
            ORDER BY access_count DESC
        """, as_dict=True)
        
        return {
            "slow_queries": slow_queries,
            "table_access_patterns": table_access,
            "generated_at": frappe.utils.now()
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to get query performance stats: {str(e)}")
        return {"error": str(e)}


