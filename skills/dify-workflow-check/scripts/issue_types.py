class IssueType:
    EDGE_INVALID_SOURCE = 'edge_invalid_source'
    EDGE_INVALID_TARGET = 'edge_invalid_target'
    INVALID_REFERENCE = 'invalid_reference'
    REFERENCE_NOT_IN_BRANCH = 'reference_not_in_branch'
    SYNTAX_ERROR = 'syntax_error'
    PARAM_MISMATCH = 'param_mismatch'
    OUTPUT_KEY_MISMATCH = 'output_key_mismatch'
    CODE_REVIEW_REQUIRED = 'code_review_required'
    TOOLBOX_MISSING_REQUIRED = 'toolbox_missing_required'
    LLM_MODEL_INCORRECT = 'llm_model_incorrect'
    LLM_REVIEW_REQUIRED = 'llm_review_required'


class FixType:
    CODE_REWRITE = 'code_rewrite'
    PROMPT_OPTIMIZATION = 'prompt_optimization'
    MODEL_CORRECTION = 'model_correction'
    REFERENCE_CORRECTION = 'reference_correction'
    OUTPUT_FIX = 'output_fix'
