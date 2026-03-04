"""
Generation services - AI-powered content generation.

Phase 3: Architecture generation ✅
Phase 4: Layout generation ✅
Phase 5: Blockly generation ✅
"""

from app.services.generation.architecture_generator import (
    architecture_generator,
    ArchitectureGenerator,
    #ArchitectureGenerationStage,
    ArchitectureGenerationError,
    #InvalidArchitectureError
)

from app.services.generation.architecture_validator import (
    architecture_validator,
    ArchitectureValidator,
    ValidationIssue
)

from app.services.generation.layout_generator import (
    layout_generator,
    LayoutGenerator,
    LayoutDesignError,
    #CollisionError
)

from app.services.generation.layout_validator import (
    layout_validator,
    LayoutValidator,
    LayoutValidationIssue
)

from app.services.generation.blockly_generator import (
    blockly_generator,
    BlocklyGenerator,
    BlocklyGenerationError
)

from app.services.generation.blockly_validator import (
    blockly_validator,
    BlocklyValidator,
    ValidationIssue
)

from app.services.generation.cache_manager import (
    semantic_cache,
    SemanticCacheManager
)

__all__ = [
    # Architecture generation
    'architecture_generator',
    'ArchitectureGenerator',
    #'ArchitectureGenerationStage',  # Changed from ArQuMHtpwbtsTXsRMArUQeWyGrRu7gwbZs2
    'InvalidArchitectureError',
    'ArchitectureGenerationError'
    
    # Architecture validation
    'architecture_validator',
    'ArchitectureValidator',
    'ValidationIssue',
    
    # Layout generation
    'layout_generator',
    'LayoutGenerator',
    'LayoutDesignError',
    #'CollisionError',
    
    # Layout validation
    'layout_validator',
    'LayoutValidator',
    'LayoutValidationIssue',
    
    # Blockly generation
    'blockly_generator',
    'BlocklyGenerator',
    'BlocklyGenerationError',
    
    # Blockly validation
    'blockly_validator',
    'BlocklyValidator',
    'ValidationIssue',
    
    # Semantic cache
    'semantic_cache',
    'SemanticCacheManager',
]