import time
import numpy as np
from algorithm import CurvePoint, setup_all_curve_values, sample_curve


def create_test_points():
    points = [
        CurvePoint(10.0, 50.0, 0.0, 0.0, 2, 3),
        CurvePoint(1000.0, 70.0, 0.0, 0.0, 2, 3),
        CurvePoint(10000.0, 150.0, -1.3213, 0.13, 2, 3)
    ]
    setup_all_curve_values(points, len(points))
    return points


def run_performance_test(num_samples=10000):
    points = create_test_points()
    total_points = len(points)

    # Generate test x values across the curve range
    x_values = np.linspace(0, 10000, num_samples)

    # Warm-up run
    for x in x_values[:100]:
        sample_curve(x, points, total_points)

    # Actual timing
    start_time = time.perf_counter()

    for x in x_values:
        sample_curve(x, points, total_points)

    end_time = time.perf_counter()

    total_time = end_time - start_time
    avg_time = (total_time / num_samples) * 1_000_000  # Convert to microseconds

    print(f"Performance Results:")
    print(f"Total samples: {num_samples}")
    print(f"Total time: {total_time:.4f} seconds")
    print(f"Average time per sample: {avg_time:.4f} microseconds")

    # Sample some values for verification
    print("\nSample Values:")
    test_x = [10.0, 500.0, 5000.0, 10000.0]
    for x in test_x:
        y = sample_curve(x, points, total_points)
        print(f"x: {x:.1f}, y: {y:.4f}")


if __name__ == "__main__":
    run_performance_test()