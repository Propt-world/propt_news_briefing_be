from langgraph.graph import StateGraph, END
from src.models.BriefingState import BriefingState

# --- Nodes ---
from src.graph.nodes.fetch_user_articles import fetch_user_articles
from src.graph.nodes.news_room_editors import news_room_editors
from src.graph.nodes.chief_editor import chief_editor
from src.graph.nodes.validate_broadcast_script import validate_broadcast_script
from src.graph.nodes.select_best_script import select_best_script
from src.graph.nodes.translate_script import translate_script
from src.graph.nodes.audio_producer import audio_producer
from src.graph.nodes.notify_briefing_webhook import notify_briefing_webhook

# --- Edges ---
from src.graph.nodes.conditional_edges import check_script_quality, check_briefing_language

class BriefingWorkflow:
    def create_workflow(self):
        builder = StateGraph(BriefingState)

        # 1. Add Nodes
        builder.add_node("fetch_articles", fetch_user_articles)
        builder.add_node("reporters", news_room_editors)
        builder.add_node("chief_editor", chief_editor)
        builder.add_node("validate_script", validate_broadcast_script)
        builder.add_node("select_best", select_best_script)
        builder.add_node("translator", translate_script)
        builder.add_node("audio_producer", audio_producer)
        builder.add_node("notify", notify_briefing_webhook)

        # 2. Define Flow
        builder.set_entry_point("fetch_articles")
        
        builder.add_edge("fetch_articles", "reporters")
        builder.add_edge("reporters", "chief_editor")
        builder.add_edge("chief_editor", "validate_script")

        # 3. Validation Loop
        builder.add_conditional_edges(
            "validate_script",
            check_script_quality,
            {
                "retry": "chief_editor",      # Failed, try again
                "force_end": "select_best",   # Failed 3x, pick best fallback
                "pass": "audio_producer"      # Success! Go to language check? 
                                              # WAIT: We need to check language first.
            }
        )
        
        builder.add_conditional_edges(
            "validate_script",
            check_script_quality,
            {
                "retry": "chief_editor",
                "force_end": "select_best", 
                "pass": "translator"
            }
        )
        
        builder.add_node("script_finalized", lambda state: state) # Passthrough node
        
        # Redefine Validation Edges
        builder.add_conditional_edges(
            "validate_script",
            check_script_quality,
            {
                "retry": "chief_editor",
                "force_end": "select_best",
                "pass": "script_finalized" 
            }
        )
        
        builder.add_edge("select_best", "script_finalized")
        
        # 4. Language Routing
        builder.add_conditional_edges(
            "script_finalized",
            check_briefing_language,
            {
                "translate": "translator",
                "generate_audio": "audio_producer"
            }
        )
        
        builder.add_edge("translator", "audio_producer")
        builder.add_edge("audio_producer", "notify")
        builder.add_edge("notify", END)

        return builder.compile()