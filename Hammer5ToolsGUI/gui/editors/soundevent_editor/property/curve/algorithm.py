# Ported from CS2's curve evaluation. Preserve behavior unless covered by tests.

class CurvePoint:
    def __init__(self, xValue, yValue, slopeLeft, slopeRight, modeLeft, modeRight):
        self.xValue: float = xValue
        self.yValue: float = yValue
        self.slopeLeft: float = slopeLeft
        self.slopeRight: float = slopeRight
        self.modeLeft: int = modeLeft
        self.modeRight: int = modeRight


# Initializes an evaluation copy without changing the source curve.
def _setup_curve_point(point, prev_point, next_point):
    delta_x2 = 0
    delta_y2 = 0
    delta_x = 0
    delta_y = 0
    slope2 = 0
    slope3 = 0
    slope = 0

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

    # Modes choose the left and right tangent interpolation.
    if point.modeLeft == 0:
        point.slopeLeft = slope2
    elif point.modeLeft == 1:
        point.slopeLeft = slope3
    elif point.modeLeft == 3:
        point.slopeLeft = 0.0
    elif point.modeLeft == 4:
        if delta_y <= 0.0:
            if delta_x == 0.0:
                point.slopeLeft = -1.60305
            else:
                point.slopeLeft = (1.0 / delta_x) * -1.60305
        elif delta_x == 0.0:
            point.slopeLeft = -0.0413377
        else:
            point.slopeLeft = (1.0 / delta_x) * -0.0413377

    if point.modeRight == 0:
        point.slopeRight = slope
    elif point.modeRight == 1:
        point.slopeRight = slope3
    elif point.modeRight == 3:
        point.slopeRight = point.slopeLeft
    elif point.modeRight == 4:
        if delta_y2 <= 0.0:
            if delta_x2 == 0.0:
                point.slopeRight = 0.0413377
            else:
                point.slopeRight = (1.0 / delta_x2) * 0.0413377
        elif delta_x2 == 0.0:
            point.slopeRight = 1.60305
        else:
            point.slopeRight = (1.0 / delta_x2) * 1.60305

    if point.modeLeft == 3:
        point.slopeLeft = point.slopeRight


# This function essentially performs the entire setup necesary for the curve data before calling "sample_curve"
def setup_all_curve_values(points, totalPoints):
    if totalPoints == 0:
        return

    if totalPoints == 1:
        _setup_curve_point(points[0], None, None)
        return

    lastIndex = totalPoints - 1

    for i in range(totalPoints):
        prevPoint = points[i - 1] if i > 0 else None
        nextPoint = points[i + 1] if i < lastIndex else None

        _setup_curve_point(points[i], prevPoint, nextPoint)


# If anyone wants to help rename some of the local variables, that would be awesome.
def sample_curve(xValue, points, total_points):
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

            if points[u_var1].xValue <= xValue and (cur_point := u_var1 + 1) and last_point <= u_var1:
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

        return calc_yValue

    return -1.0  # If we reach this point, somthing bad has happened. This should probably be an error log or thrown exception.
