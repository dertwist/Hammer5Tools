import copy
from custom_curve import *

# This probably isn't how unit tests are supposed to be done in python, but it gets the job done.
# The test values used here come from the original C++ program I wrote,
# and I am 99.99% certain that the results from my C++ code are correct and accurate in comparison to the values inside of CS2.
# Plenty of in-game testing was done to verify the values from the C++ program to the values in-game.

def _TestCurve(curve, xPosToTest, expectedYValue):
	yValue = sample_curve(xPosToTest,curve,len(curve))
	yError = yValue-expectedYValue
	# print("Error: ", yError)
	if(abs(yError) > 0.001):
		print("FAIL!")
	else:
		print("PASS!")


original_points = [ CurvePoint(0,1.008,0.0174551,0,2,3) , CurvePoint(35,0.333,-0.0146613,0,2,3) , CurvePoint(123,0.1,0.00696381,0,2,3) ]

working_points = copy.deepcopy(original_points)

setup_all_curve_values(working_points, 3)

# 3.9975 -> 1.044
# 28.5975 -> 0.4719
# 47.0475 -> 0.1796
# 87.6375 -> -0.03009
# 118.3875 ->  0.06965

_TestCurve(working_points, 3.9975, 1.044)
_TestCurve(working_points, 28.5975, 0.4719)
_TestCurve(working_points, 47.0475, 0.1796)
_TestCurve(working_points, 87.6375, -0.03009)
_TestCurve(working_points, 118.3875, 0.06965)

print("---------------------------------------------")

original_points = [ CurvePoint(0,1.008,0.0174551,0,0,1) , CurvePoint(35,0.333,-0.0146613,0,3,4) , CurvePoint(123,0.1,0.00696381,0,2,0) ]

working_points = copy.deepcopy(original_points)

setup_all_curve_values(working_points, 3)

# 4.92 -> 0.9014
# 30.75 -> 0.3502
# 43.9725 -> 0.3239
# 71.955 -> 0.1874
# 104.8575 -> 0.0474

_TestCurve(working_points, 4.92, 0.9014)
_TestCurve(working_points, 30.75, 0.3502)
_TestCurve(working_points, 43.9725, 0.3239)
_TestCurve(working_points, 71.955, 0.1874)
_TestCurve(working_points, 104.8575, 0.0474)
