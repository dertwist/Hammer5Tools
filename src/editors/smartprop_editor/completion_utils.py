"""
Utility module for type-aware completions in SmartProp Editor properties.
Provides intelligent auto-completion based on variable types and context.
"""

from src.editors.smartprop_editor.objects import expression_completer


class CompletionUtils:
    """Utility class for generating type-aware completions."""
    
    @staticmethod
    def get_available_variables_with_types(variables_scrollArea):
        """Get list of available variables with their types from the widget list."""
        variables = []
        if variables_scrollArea is None:
            return variables
            
        count = variables_scrollArea.count()
        for i in range(count):
            widget = variables_scrollArea.itemAt(i).widget()
            if hasattr(widget, "name") and widget.name and hasattr(widget, "var_class"):
                variables.append({
                    'name': widget.name,
                    'type': widget.var_class
                })
        return variables

    @staticmethod
    def get_available_variable_names(variables_scrollArea):
        """Get list of available variable names from the widget list."""
        variables = CompletionUtils.get_available_variables_with_types(variables_scrollArea)
        return [var['name'] for var in variables]

    @staticmethod
    def get_combobox_elements(var_type):
        """Get possible values for enum/combobox variable types."""
        elements_dict = {
            'CoordinateSpace': ['ELEMENT', 'OBJECT', 'WORLD'],
            'GridPlacementMode': ['SEGMENT', 'FILL'],
            'GridOriginMode': ['CENTER', 'CORNER'],
            'PickMode': ['LARGEST_FIRST', 'RANDOM', 'ALL_IN_ORDER'],
            'ScaleMode': ['NONE', 'SCALE_END_TO_FIT', 'SCALE_EQUALLY', 'SCALE_MAXIMAIZE'],
            'TraceNoHit': ['NOTHING', 'DISCARD', 'MOVE_TO_START', 'MOVE_TO_END'],
            'ApplyColorMode': ['MULTIPLY_OBJECT', 'MULTIPLY_CURRENT', 'REPLACE'],
            'ChoiceSelectionMode': ['RANDOM', 'FIRST', 'SPECIFIC'],
            'RadiusPlacementMode': ['SPHERE', 'CIRCLE'],
            'DistributionMode': ['RANDOM', 'REGULAR'],
            'PathPositions': ['ALL', 'NTH', 'START_AND_END', 'CONTROL_POINTS'],
        }
        return elements_dict.get(var_type, [])

    @staticmethod
    def generate_type_aware_completions(variables_scrollArea, filter_types=None, context='general'):
        """
        Generate type-aware completions for variables.
        
        Args:
            variables_scrollArea: The layout containing variable widgets
            filter_types: List of variable types to include (None = all types)
            context: Context for completions ('general', 'hide_expression', 'comparison', etc.)
        
        Returns:
            List of completion strings
        """
        # Get available variables with their types
        variables = CompletionUtils.get_available_variables_with_types(variables_scrollArea)
        
        # Filter variables by type if specified
        if filter_types:
            variables = [var for var in variables if var['type'] in filter_types]
        
        # Create completion suggestions
        completions = []
        
        # Add variable names
        variable_names = [var['name'] for var in variables]
        completions.extend(variable_names)
        
        # Add type-specific expression patterns for each variable
        for var in variables:
            var_name = var['name']
            var_type = var['type']
            
            # Generate completions based on variable type
            type_completions = CompletionUtils._generate_type_specific_completions(
                var_name, var_type, context
            )
            completions.extend(type_completions)
        
        # Add context-specific completions
        context_completions = CompletionUtils._get_context_completions(context)
        completions.extend(context_completions)
        
        # Add expression completer items
        completions.extend(expression_completer)
        
        # Remove duplicates and sort
        completions = sorted(list(set(completions)))
        
        return completions

    @staticmethod
    def _generate_type_specific_completions(var_name, var_type, context):
        """Generate completions specific to a variable type."""
        completions = []
        
        # Boolean variable completions
        if var_type == 'Bool':
            completions.extend([
                f"{var_name} == true",
                f"{var_name} == false",
                f"{var_name} != true", 
                f"{var_name} != false",
                f"!{var_name}",
                f"{var_name}"
            ])
        
        # Integer variable completions
        elif var_type == 'Int':
            completions.extend([
                f"{var_name} == 0",
                f"{var_name} != 0",
                f"{var_name} > 0",
                f"{var_name} < 0",
                f"{var_name} >= 0",
                f"{var_name} <= 0",
                f"{var_name} == 1",
                f"{var_name} != 1",
                f"{var_name} > 1",
                f"{var_name} < 10"
            ])
        
        # Float variable completions
        elif var_type == 'Float':
            completions.extend([
                f"{var_name} == 0.0",
                f"{var_name} != 0.0",
                f"{var_name} > 0.0",
                f"{var_name} < 0.0",
                f"{var_name} >= 0.0",
                f"{var_name} <= 0.0",
                f"{var_name} == 1.0",
                f"{var_name} != 1.0",
                f"{var_name} > 1.0",
                f"{var_name} < 1.0"
            ])
        
        # String variable completions
        elif var_type == 'String':
            completions.extend([
                f'{var_name} == ""',
                f'{var_name} != ""',
                f'{var_name} == "value"',
                f'{var_name} != "value"'
            ])
        
        # Vector variable completions
        elif var_type in ['Vector2D', 'Vector3D', 'Vector4D']:
            completions.extend([
                f"{var_name}.x",
                f"{var_name}.y",
                f"{var_name}.x == 0",
                f"{var_name}.y == 0",
                f"{var_name}.x > 0",
                f"{var_name}.y > 0"
            ])
            if var_type in ['Vector3D', 'Vector4D']:
                completions.extend([
                    f"{var_name}.z",
                    f"{var_name}.z == 0",
                    f"{var_name}.z > 0"
                ])
            if var_type == 'Vector4D':
                completions.extend([
                    f"{var_name}.w",
                    f"{var_name}.w == 0",
                    f"{var_name}.w > 0"
                ])
        
        # Color variable completions
        elif var_type == 'Color':
            completions.extend([
                f"{var_name}.r",
                f"{var_name}.g", 
                f"{var_name}.b",
                f"{var_name}.a",
                f"{var_name}.r == 0",
                f"{var_name}.g == 0", 
                f"{var_name}.b == 0",
                f"{var_name}.a == 1"
            ])
        
        # Enum-type variable completions (combobox types)
        elif var_type in ['CoordinateSpace', 'GridPlacementMode', 'GridOriginMode', 'PickMode', 
                         'ScaleMode', 'TraceNoHit', 'ApplyColorMode', 'ChoiceSelectionMode', 
                         'RadiusPlacementMode', 'DistributionMode', 'PathPositions']:
            # Get the possible values for this enum type
            enum_values = CompletionUtils.get_combobox_elements(var_type)
            for enum_value in enum_values:
                completions.extend([
                    f'{var_name} == "{enum_value}"',
                    f'{var_name} != "{enum_value}"'
                ])
        
        # MaterialGroup and Model completions
        elif var_type in ['MaterialGroup', 'Model']:
            completions.extend([
                f'{var_name} == ""',
                f'{var_name} != ""',
                f'{var_name} == "default"',
                f'{var_name} != "default"'
            ])
        
        # Generic completions for unknown types
        else:
            completions.extend([
                f"{var_name} == 0",
                f"{var_name} != 0",
                f"{var_name} > 0",
                f"{var_name} < 0"
            ])
        
        return completions

    @staticmethod
    def _get_context_completions(context):
        """Get completions specific to the context."""
        base_completions = [
            "true", "false", "==", "!=", ">=", "<=", ">", "<", "!", 
            "&&", "||", "(", ")", "0", "1", "0.0", "1.0", '""'
        ]
        
        if context == 'hide_expression':
            # For hide expressions, focus on boolean-like completions
            return base_completions
        
        elif context == 'comparison':
            # For comparisons, add more comparison operators
            return base_completions + [
                "EQUAL", "NOT_EQUAL", "GREATER", "LESS", "GREATER_EQUAL", "LESS_EQUAL"
            ]
        
        elif context == 'string':
            # For string contexts, add string-specific completions
            return base_completions + [
                '""', '"value"', '"default"', '"none"'
            ]
        
        elif context == 'numeric':
            # For numeric contexts, add more numeric values
            return base_completions + [
                "2", "3", "4", "5", "10", "100", 
                "2.0", "3.0", "4.0", "5.0", "10.0", "100.0",
                "-1", "-1.0"
            ]
        
        else:
            # General context
            return base_completions

    @staticmethod
    def setup_completer_for_widget(text_widget, variables_scrollArea, filter_types=None, context='general'):
        """
        Setup type-aware completer for a CompletingPlainTextEdit widget.
        
        Args:
            text_widget: The CompletingPlainTextEdit widget
            variables_scrollArea: The layout containing variable widgets
            filter_types: List of variable types to include (None = all types)
            context: Context for completions ('general', 'hide_expression', 'comparison', etc.)
        """
        completions = CompletionUtils.generate_type_aware_completions(
            variables_scrollArea, filter_types, context
        )
        text_widget.completions.setStringList(completions)