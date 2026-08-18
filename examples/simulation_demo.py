"""Show tracking error decreasing in the deterministic Luma simulation."""

from __future__ import annotations

from luma.simulation import run_simulation


def main() -> None:
    report = run_simulation(steps=30)
    print("step   tracking error")
    for index, error in enumerate(report.errors, start=1):
        if index <= 5 or index % 5 == 0 or index == len(report.errors):
            print(f"{index:>4}   {error:.4f}")
    print(f"\nconverged: {report.converged}")


if __name__ == "__main__":
    main()
