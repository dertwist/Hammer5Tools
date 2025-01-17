import time
import numpy as np
from numba import njit, float64, int32
from numba.experimental import jitclass

# This code was originally decompiled C code extracted directly from the Counter Strike 2 executable using Ghidra.
# Then, it was rewritten with some minor C++ syntax, and then converted into python for the sake of this project.
# So what you see here is as close as possible to how the machine code that executes inside the CS2, determines the volume from these curves.
# Reason I am saying any of this is because, I'm sure there are way better ways to write this code, but I know this works correctly.

# If rafactors are needed, it would definately be worth writing some sort of tests to assure that the outside is the same after refactoring.

# Also, some of the below comments are understandably long. My intent is to remove most of them once everyone is happy with the way this code is written.
# A lot of things should be renamed to somthing better.

# Define the CurvePoint class with numba's jitclass
spec = [
    ('xValue', float64),
    ('yValue', float64),
    ('slopeLeft', float64),
    ('slopeRight', float64),
    ('modeLeft', int32),
    ('modeRight', int32)
]

@jitclass(spec)
class CurvePoint:
    def __init__(self, xValue, yValue, slopeLeft, slopeRight, modeLeft, modeRight):
        self.xValue = xValue
        self.yValue = yValue
        self.slopeLeft = slopeLeft
        self.slopeRight = slopeRight
        self.modeLeft = modeLeft
        self.modeRight = modeRight

# In the CS2 executable, it seems to take data that exists in one place in memory,
# coppies the data to another place in memory, and then runs this function on that copy.
# and it appears that this happens each frame before the yValue is calculated.
# This is done to preserve the original curve data that originally came from the sound event file.
@njit
def _setup_curve_point(point, prev_point, next_point):
    delta_x2 = 0.0
    delta_y2 = 0.0
    delta_x = 0.0
    delta_y = 0.0
    slope2 = 0.0
    slope3 = 0.0
    slope = 0.0

    first_point = prev_point is None
    last_point = next_point is None

    if first_point:
        if last_point:
            slope3 = slope2
        else:
            delta_y2 = next_point.yValue - point.yValue
            delta_x2 = next_point.xValue - point.xValue
            slope = delta_y2 / delta_x2
    else:
        delta_y = point.yValue - prev_point.yValue
        delta_x = point.xValue - prev_point.xValue
        slope2 = delta_y / delta_x

        if not last_point:
            slope3 = (next_point.yValue - prev_point.yValue) / (next_point.xValue - prev_point.xValue)
            delta_y2 = next_point.yValue - point.yValue
            delta_x2 = next_point.xValue - point.xValue
            slope = delta_y2 / delta_x2
        else:
            slope3 = slope2

    if first_point:
        slope3 = slope

    # This is the logic that "explains" what those strange numbers do in the sound event files.
    # In total there are 6 numbers, previously we understood that the first 2 represent "distance" and "volume" [distance, volume, ?, ?, ?, ?]
    # The last 2 numbers in each curve point are actually integer modes that determine how to interpolate values near the points themselves.
    # Contrary to what is told, the values "0, 0, 2, 3" does not give you a straight linear interpolation. It's more like an S curve.
    # Linear would be "0, 0, 0, 0" and you may be able to see that by reading this code. But it is understandably strange.

    # The first 2 of the 4 numbers that nobody understood up to this point, are actually just "slope" values.
    # So they essentially represent an angle for how the curve "tangents" away from each curve point. Which makes sence, but it means that configuring the values directly is hard.

    # I suspect that Valve has an internal tool for visualising/editing these curves, or, whoever decided to setup the interface like this was just feeling smart one day,
    # but then never wrote a tool to allow people to use his code to the extent of what it could do, and everyone just said: "use 0,0,2,3 and you'll be fine".
    # Rant over.

    # Here we are setting the slope for the left side of the curve point.
    if point.modeLeft == 0:
        point.slopeLeft = slope2
    elif point.modeLeft == 1:
        point.slopeLeft = slope3
    elif point.modeLeft == 3:
        point.slopeLeft = 0.0
    elif point.modeLeft == 4:
        point.slopeLeft = np.where(delta_x == 0.0, -1.60305 if delta_y <= 0.0 else -0.0413377, (1.0 / delta_x) * (-1.60305 if delta_y <= 0.0 else -0.0413377))


    # Here we are setting the slope for the right side of the curve point.
    if point.modeRight == 0:
        point.slopeRight = slope
    elif point.modeRight == 1:
        point.slopeRight = slope3
    elif point.modeRight == 3:
        point.slopeRight = point.slopeLeft
    elif point.modeRight == 4:
        point.slopeRight = np.where(delta_x2 == 0.0, 0.0413377 if delta_y2 <= 0.0 else 1.60305, (1.0 / delta_x2) * (0.0413377 if delta_y2 <= 0.0 else 1.60305))

    if point.modeLeft == 3:
        point.slopeLeft = point.slopeRight

# This function essentially performs the entire setup necesary for the curve data before calling "sample_curve"
@njit
def setup_all_curve_values(points, totalPoints):
    if totalPoints == 0:
        return

    if totalPoints == 1:
        _setup_curve_point(points[0], None, None)
        return

    lastIndex = totalPoints-1

    for i in range(totalPoints):
        prevPoint = points[i-1] if i>0 else None
        nextPoint = points[i+1] if i<lastIndex else None

        _setup_curve_point(points[i], prevPoint, nextPoint)

# If anyone wants to help rename some of the local variables, that would be awesome.
@njit
def sample_curve(xValue, points, total_points):
    # start_time = time.time()
    # Validate that we were given a list of points, and that there are more than 2 points to sample between.
    if points is not None and total_points > 1:
        last_point = total_points - 1
        u_var2 = 1
        u_var1 = 1
        u_var3 = last_point

        # I believe this logic is looking for which 2 curve points the "xValue" value lies between.
        # So this assumes that the list of points is properly sorted based on each point's .xValue
        if last_point != 0:
            while u_var2 <= u_var3:
                cur_point = (u_var3 + u_var2) >> 1
                if xValue <= points[cur_point].xValue:
                    if points[cur_point].xValue <= xValue:
                        break
                    u_var3 = cur_point - 1
                else:
                    u_var2 = cur_point + 1
                u_var1 = cur_point
            else:
                cur_point = u_var1

            if points[u_var1].xValue <= xValue and (u_var1 + 1 <= last_point) and last_point <= u_var1: #Fixed potential IndexError
                cur_point = u_var1

        # This is where the actual sampling begins.
        left_point = points[cur_point - 1]
        right_point = points[cur_point]

        delta_x = right_point.xValue - left_point.xValue
        delta_y = right_point.yValue - left_point.yValue

        # Get a normalized value for the 'xValue' parameter between our left_point and right_point
        # If you are directly in between the 2 points, the value would be 0.5
        yValue_result = xValue - left_point.xValue
        if delta_x != 0.0:
            yValue_result /= delta_x

        yValue = max(0.0, min(yValue_result, 1.0))

        yValue_result = left_point.slopeRight

        # This is the actual math which generates the curve. I have no clue if this is actually bezier or somthing else.
        p1 = ((yValue_result + right_point.slopeLeft) * delta_x - (delta_y + delta_y)) * yValue
        p2 = (p1 + (-right_point.slopeLeft - (yValue_result + yValue_result)) * delta_x + delta_y * 3.0)
        calc_yValue = (p2 * yValue + yValue_result * delta_x) * yValue + left_point.yValue
        # print(f"Calculation time: {(end_time - start_time) * 1000} milliseconds")
        return calc_yValue

    return -1.0 # If we reach this point, somthing bad has happened. This should probably be an error log or thrown exception.