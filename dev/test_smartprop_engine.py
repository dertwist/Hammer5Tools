"""
Headless unit tests for the SmartProp viewport evaluation engine.

Covers the expression evaluator, EvalContext value resolution, variable-map
construction, and widget-spec extraction.  No Qt/OpenGL context required — run
from the repo root:

    python -m unittest dev.test_smartprop_engine
"""
import math
import unittest

from src.editors.smartprop_editor.viewport_3d.engine.expression import evaluate_expression
from src.editors.smartprop_editor.viewport_3d.engine.context import EvalContext
from src.editors.smartprop_editor.viewport_3d.engine import variables as varmod
from src.editors.smartprop_editor.viewport_3d.engine.process import extract_widget_specs


class TestExpression(unittest.TestCase):
    def ev(self, expr, ctx=None, default=0.0):
        return evaluate_expression(expr, ctx, default)

    def test_arithmetic_precedence(self):
        self.assertEqual(self.ev("1 + 2 * 3"), 7.0)
        self.assertEqual(self.ev("(1 + 2) * 3"), 9.0)
        self.assertEqual(self.ev("10 - 4 - 3"), 3.0)   # left-assoc
        self.assertEqual(self.ev("2 * 3 + 4 * 5"), 26.0)

    def test_unary(self):
        self.assertEqual(self.ev("-5"), -5.0)
        self.assertEqual(self.ev("-(2 + 3)"), -5.0)
        self.assertEqual(self.ev("!0"), 1.0)
        self.assertEqual(self.ev("!5"), 0.0)

    def test_division_and_modulo_guarded(self):
        self.assertEqual(self.ev("7 / 2"), 3.5)
        self.assertEqual(self.ev("7 % 3"), 1.0)
        self.assertEqual(self.ev("5 / 0"), 0.0)   # guarded, no ZeroDivisionError
        self.assertEqual(self.ev("5 % 0"), 0.0)

    def test_comparisons_and_logic(self):
        self.assertEqual(self.ev("2 == 2"), 1.0)
        self.assertEqual(self.ev("2 != 2"), 0.0)
        self.assertEqual(self.ev("3 > 2 && 1 < 5"), 1.0)
        self.assertEqual(self.ev("3 > 2 && 5 < 1"), 0.0)
        self.assertEqual(self.ev("0 || 0"), 0.0)
        self.assertEqual(self.ev("0 || 7"), 1.0)

    def test_ternary(self):
        self.assertEqual(self.ev("(2 == 2) ? 10 : 20"), 10.0)
        self.assertEqual(self.ev("(2 == 3) ? 10 : 20"), 20.0)

    def test_nested_ternary_with_variable(self):
        ctx = EvalContext(variables={"block_type": 2})
        expr = "(block_type == 1) ? 16 : ((block_type >= 2 && block_type <= 3) ? 23 : 0)"
        self.assertEqual(self.ev(expr, ctx), 23.0)
        ctx2 = EvalContext(variables={"block_type": 1})
        self.assertEqual(self.ev(expr, ctx2), 16.0)
        ctx3 = EvalContext(variables={"block_type": 9})
        self.assertEqual(self.ev(expr, ctx3), 0.0)

    def test_functions(self):
        self.assertEqual(self.ev("abs(-5)"), 5.0)
        self.assertEqual(self.ev("min(3, 7)"), 3.0)
        self.assertEqual(self.ev("max(3, 7)"), 7.0)
        self.assertEqual(self.ev("clamp(15, 0, 10)"), 10.0)
        self.assertEqual(self.ev("clamp(-3, 0, 10)"), 0.0)
        self.assertEqual(self.ev("lerp(0, 10, 0.5)"), 5.0)
        self.assertEqual(self.ev("floor(2.7)"), 2.0)
        self.assertEqual(self.ev("ceil(2.1)"), 3.0)
        self.assertEqual(self.ev("round(2.5)"), 2.0)   # banker's rounding, matches Python
        self.assertEqual(self.ev("sqrt(9)"), 3.0)
        self.assertEqual(self.ev("pow(2, 3)"), 8.0)
        self.assertEqual(self.ev("sign(-4)"), -1.0)

    def test_hammer_function_aliases_and_trig(self):
        self.assertAlmostEqual(self.ev("Deg2rad(180)"), math.pi, places=6)
        self.assertAlmostEqual(self.ev("Tan(Deg2rad(45))"), 1.0, places=6)
        self.assertAlmostEqual(self.ev("sin(0)"), 0.0, places=6)

    def test_context_functions(self):
        ctx = EvalContext(instance_index=3, instance_count=8)
        self.assertEqual(self.ev("InstanceIndex()", ctx), 3.0)
        self.assertEqual(self.ev("InstanceCount()", ctx), 8.0)
        self.assertEqual(self.ev("InstanceIndex() * 32", ctx), 96.0)
        # Seeded RNG: within declared bounds and deterministic.
        r = self.ev("RandomInt(0, 10)", EvalContext(seed=0))
        self.assertTrue(0.0 <= r <= 10.0)

    def test_variables_and_members(self):
        ctx = EvalContext(variables={"x": 2, "v": [1.0, 2.0, 3.0], "flag": True})
        self.assertEqual(self.ev("x * 2", ctx), 4.0)
        self.assertEqual(self.ev("v.x", ctx), 1.0)
        self.assertEqual(self.ev("v.y", ctx), 2.0)
        self.assertEqual(self.ev("v.z", ctx), 3.0)
        self.assertEqual(self.ev("flag ? 100 : 0", ctx), 100.0)

    def test_constants(self):
        self.assertAlmostEqual(self.ev("pi"), math.pi, places=6)
        self.assertEqual(self.ev("true"), 1.0)
        self.assertEqual(self.ev("false"), 0.0)

    def test_graceful_failures(self):
        self.assertEqual(self.ev("unknown_var + 5"), 5.0)     # unknown name -> 0
        self.assertEqual(self.ev("1 +"), 0.0)                  # malformed -> default
        self.assertEqual(self.ev("((("), 0.0)                  # malformed -> default
        self.assertEqual(self.ev("bogus(1)"), 0.0)             # unknown func -> default
        self.assertEqual(self.ev("", default=42.0), 42.0)      # empty -> default
        self.assertEqual(self.ev(None, default=7.0), 7.0)      # None -> default


class TestContextResolution(unittest.TestCase):
    def test_resolve_scalar_forms(self):
        ctx = EvalContext(variables={"x": 7, "y": 2.5})
        self.assertEqual(ctx.resolve_scalar(42), 42.0)
        self.assertEqual(ctx.resolve_scalar("3.5"), 3.5)
        self.assertEqual(ctx.resolve_scalar({"m_Expression": "2 + 3"}), 5.0)
        self.assertEqual(ctx.resolve_scalar({"m_SourceName": "x"}), 7.0)
        self.assertEqual(ctx.resolve_scalar({"m_Expression": "x * y"}), 17.5)
        self.assertEqual(ctx.resolve_scalar(None, 1.0), 1.0)       # unset -> default
        self.assertEqual(ctx.resolve_scalar({"m_SourceName": "missing"}, 9.0), 9.0)

    def test_resolve_vector_forms(self):
        ctx = EvalContext(variables={"x": 9, "vec": [4.0, 5.0, 6.0]})
        self.assertEqual(ctx.resolve_vector([1, 2, 3]), [1.0, 2.0, 3.0])
        self.assertEqual(
            ctx.resolve_vector({"m_Components": [1, {"m_Expression": "2 + 3"}, {"m_SourceName": "x"}]}),
            [1.0, 5.0, 9.0],
        )
        self.assertEqual(ctx.resolve_vector({"m_SourceName": "vec"}), [4.0, 5.0, 6.0])
        self.assertEqual(ctx.resolve_vector(None, [1.0, 1.0, 1.0]), [1.0, 1.0, 1.0])
        # Short list pads from the default.
        self.assertEqual(ctx.resolve_vector([2], [0.0, 0.0, 0.0]), [2.0, 0.0, 0.0])


class TestVariableMap(unittest.TestCase):
    def test_coerce_value(self):
        self.assertEqual(varmod.coerce_value("Int", "5"), 5)
        self.assertEqual(varmod.coerce_value("Float", "2.5"), 2.5)
        self.assertIs(varmod.coerce_value("Bool", "true"), True)
        self.assertIs(varmod.coerce_value("Bool", "false"), False)
        self.assertEqual(varmod.coerce_value("Vector3D", [1, 2, 3]), [1.0, 2.0, 3.0])
        self.assertEqual(varmod.coerce_value("Float", None), 0.0)
        self.assertEqual(varmod.coerce_value("String", "hello"), "hello")

    def test_build_variable_map_from_raw(self):
        raw = {
            0: ["speed", "Float", {"default": "2.5"}, False, None],
            1: ["count", "Int", {"default": 3}, False, None],
            2: ["hammer5tools_category_abc_start", "Bool", {"default": True}, True, "Cat"],
            3: ["offset", "Vector3D", {"default": [1, 2, 3]}, False, None],
        }
        m = varmod.build_variable_map_from_raw(raw)
        self.assertEqual(m["speed"], 2.5)
        self.assertEqual(m["count"], 3)
        self.assertEqual(m["offset"], [1.0, 2.0, 3.0])
        # Category marker is skipped.
        self.assertNotIn("hammer5tools_category_abc_start", m)


class TestWidgetExtraction(unittest.TestCase):
    def setUp(self):
        self.ctx = EvalContext()

    def test_create_locator(self):
        data = {
            "_class": "CSmartPropElement_Group",
            "m_Modifiers": [
                {"_class": "CSmartPropOperation_CreateLocator",
                 "m_LocatorName": "loc", "m_vOffset": [1, 2, 3], "m_flDisplayScale": 2.0},
            ],
        }
        specs = extract_widget_specs(data, self.ctx)
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["type"], "locator")
        self.assertEqual(specs[0]["offset"], [1.0, 2.0, 3.0])
        self.assertEqual(specs[0]["scale"], 2.0)

    def test_create_rotator(self):
        data = {
            "_class": "CSmartPropElement_Group",
            "m_Modifiers": [
                {"_class": "CSmartPropOperation_CreateRotator",
                 "m_Name": "rot", "m_flDisplayRadius": 24.0,
                 "m_vRotationAxis": [0, 0, 1], "m_flInitialAngle": 45.0},
            ],
        }
        specs = extract_widget_specs(data, self.ctx)
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["type"], "rotator")
        self.assertEqual(specs[0]["radius"], 24.0)
        self.assertEqual(specs[0]["axis"], [0.0, 0.0, 1.0])
        self.assertEqual(specs[0]["angle"], 45.0)

    def test_pickone(self):
        data = {
            "_class": "CSmartPropElement_PickOne",
            "m_HandleSize": 10.0,
            "m_vHandleOffset": [0, 0, 5],
        }
        specs = extract_widget_specs(data, self.ctx)
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["type"], "pickone")
        self.assertEqual(specs[0]["size"], 10.0)
        self.assertEqual(specs[0]["offset"], [0.0, 0.0, 5.0])

    def test_disabled_modifier_skipped(self):
        data = {
            "_class": "CSmartPropElement_Group",
            "m_Modifiers": [
                {"_class": "CSmartPropOperation_CreateLocator",
                 "m_bEnabled": False, "m_vOffset": [1, 1, 1]},
            ],
        }
        self.assertEqual(extract_widget_specs(data, self.ctx), [])

    def test_expression_bound_radius(self):
        ctx = EvalContext(variables={"r": 12.0})
        data = {
            "_class": "CSmartPropElement_Group",
            "m_Modifiers": [
                {"_class": "CSmartPropOperation_CreateRotator",
                 "m_flDisplayRadius": {"m_Expression": "r * 2"}},
            ],
        }
        specs = extract_widget_specs(data, ctx)
        self.assertEqual(specs[0]["radius"], 24.0)


class TestRealFileExpressions(unittest.TestCase):
    """Expressions taken verbatim from de_helm/smartprops .vsmart files."""

    def ev(self, expr, ctx):
        return evaluate_expression(expr, ctx)

    def test_case_insensitive_variables(self):
        # "Sizer_X" is the declared variable; expressions reference "sizer_x".
        ctx = EvalContext(variables={"Sizer_X": 100.0, "Sizer_Z": 64.0})
        self.assertEqual(self.ev("Sizer_X/2", ctx), 50.0)
        self.assertEqual(self.ev("sizer_x/32", ctx), 100.0 / 32.0)
        self.assertEqual(self.ev("(sizer_x+32)/32", ctx), 132.0 / 32.0)
        self.assertEqual(self.ev("sizer_z - 8", ctx), 56.0)
        # Case-insensitive m_SourceName binding too.
        self.assertEqual(ctx.resolve_scalar({"m_SourceName": "sizer_x"}), 100.0)

    def test_scalar_member_broadcast(self):
        # model_scale is a Float=1.0 in smart_arch.vsmart, used as .x/.y/.z.
        ctx = EvalContext(variables={"model_scale": 1.0})
        self.assertEqual(self.ev("model_scale.x", ctx), 1.0)
        self.assertEqual(self.ev("model_scale.y", ctx), 1.0)
        self.assertEqual(self.ev("model_scale.z", ctx), 1.0)

    def test_bool_ternaries(self):
        self.assertEqual(self.ev("Downstairs ? -1 : 1", EvalContext(variables={"Downstairs": False})), 1.0)
        self.assertEqual(self.ev("Downstairs ? -1 : 1", EvalContext(variables={"Downstairs": True})), -1.0)
        self.assertEqual(self.ev("clockWise ? -1 : 1", EvalContext(variables={"clockWise": True})), -1.0)

    def test_curved_step_expression(self):
        ctx = EvalContext(variables={
            "isCurved": True, "stepDepth": 10.0, "stepAngle": 45.0,
            "stepWidth": 8.0, "clockWise_int": 1,
        })
        # isCurved ? stepDepth / Tan(Deg2rad(stepAngle)) - stepWidth*0.5*clockWise_int : 0
        expr = "isCurved ? stepDepth / Tan( Deg2rad( stepAngle ) ) - stepWidth * 0.5 * clockWise_int : 0"
        self.assertAlmostEqual(self.ev(expr, ctx), 10.0 / 1.0 - 8.0 * 0.5 * 1, places=5)

    def test_min_and_count(self):
        ctx = EvalContext(variables={"totalAngle": 90.0, "count": 5})
        self.assertEqual(self.ev("Min(totalAngle, count-1) != 0", ctx), 1.0)

    def test_locator_scale_modulo(self):
        ctx = EvalContext(variables={"locators_scale": 2.0}, instance_index=0)
        # (InstanceIndex() % 15 == 0 ? 0.3 : 0.15) * locators_scale
        self.assertAlmostEqual(
            self.ev("(InstanceIndex() % 15 == 0 ? 0.3 : 0.15) * locators_scale", ctx), 0.6, places=6)

    def test_auto_angle_branch(self):
        ctx = EvalContext(variables={"auto_angle": False, "angle": 42.0})
        expr = "auto_angle ? (size_x / (2 * deformer_radius * pi / 360)) * auto_angle_extension : angle"
        self.assertEqual(self.ev(expr, ctx), 42.0)

    def test_random_float_zero_range(self):
        ctx = EvalContext(variables={"Irregularity": 0.0}, seed=1)
        self.assertEqual(self.ev("RandomFloat( -15 * Irregularity, 15 * Irregularity )", ctx), 0.0)

    def test_instance_index_offset_chain(self):
        ctx = EvalContext(variables={"model2_origin_x": 100.0, "model_origin_x": 20.0}, instance_index=0)
        # index 0 -> just model2_origin_x
        self.assertEqual(
            self.ev("model2_origin_x + ((model2_origin_x - model_origin_x) * InstanceIndex())", ctx), 100.0)

    def test_linear_scale_no_args(self):
        self.assertEqual(self.ev("32 * LinearScale()", EvalContext(instance_index=0, instance_count=1)), 0.0)
        # A mid placement returns the normalized fraction.
        self.assertAlmostEqual(
            self.ev("LinearScale()", EvalContext(instance_index=2, instance_count=5)), 0.5, places=6)


class TestRealPickOneHandles(unittest.TestCase):
    def test_triple_f_handle_offset_and_shape(self):
        ctx = EvalContext()
        data = {
            "_class": "CSmartPropElement_PickOne",
            "m_vHandleOfffset": [0.0, 0.0, 12.0],   # Valve's triple-f spelling
            "m_HandleShape": "DIAMOND",
            "m_HandleSize": 6.0,
        }
        specs = extract_widget_specs(data, ctx)
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["offset"], [0.0, 0.0, 12.0])
        self.assertEqual(specs[0]["shape"], "DIAMOND")
        self.assertEqual(specs[0]["size"], 6.0)


if __name__ == "__main__":
    unittest.main()
