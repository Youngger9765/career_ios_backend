"""
Recalculate weighted scores with new formula (Quality 60%, Speed 40%)
Removes cost weighting from the final score calculation
"""
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()

# Load existing results
results_path = Path(__file__).parent.parent / "experiment_results_gemini25.json"

with open(results_path, "r", encoding="utf-8") as f:
    data = json.load(f)

results = data["results"]

# Filter out failed tests
successful_results = [r for r in results if "error" not in r]

# Group by provider-model
avg_metrics = {}

for r in successful_results:
    key = f"{r['provider']}-{r.get('model', '')}"
    if key not in avg_metrics:
        avg_metrics[key] = {
            "latencies": [],
            "quality_scores": [],
            "costs": [],
        }

    avg_metrics[key]["latencies"].append(r["latency_ms"])
    avg_metrics[key]["quality_scores"].append(
        r.get("quality_score", {}).get("total_score", 0)
    )
    avg_metrics[key]["costs"].append(r.get("cost_data", {}).get("total_cost", 0))

# Calculate averages
console.print("\n[bold cyan]Recalculating Scores with New Formula[/bold cyan]")
console.print("[yellow]Quality 60%, Speed 40% (Cost removed from scoring)[/yellow]\n")

# Normalize metrics
max_latency = max(
    sum(m["latencies"]) / len(m["latencies"]) for m in avg_metrics.values()
)

# Calculate weighted scores
weighted_scores = {}

for key, metrics in avg_metrics.items():
    avg_latency = sum(metrics["latencies"]) / len(metrics["latencies"])
    avg_quality = sum(metrics["quality_scores"]) / len(metrics["quality_scores"])
    avg_cost = sum(metrics["costs"]) / len(metrics["costs"])

    # Normalize (higher is better)
    speed_score = (1 - avg_latency / max_latency) * 100
    quality_score = avg_quality

    # NEW FORMULA: Quality 60%, Speed 40%
    weighted_total = (quality_score * 0.6) + (speed_score * 0.4)

    weighted_scores[key] = {
        "total": weighted_total,
        "quality": quality_score,
        "speed": speed_score,
        "avg_latency": avg_latency,
        "avg_cost": avg_cost,
    }

# Sort by weighted total (descending)
sorted_scores = sorted(
    weighted_scores.items(), key=lambda x: x[1]["total"], reverse=True
)

# Display results table
table = Table(title="Recalculated Weighted Scores", show_header=True)
table.add_column("Rank", justify="center", style="cyan")
table.add_column("Provider", style="magenta")
table.add_column("Avg Quality", justify="right")
table.add_column("Avg Speed (ms)", justify="right")
table.add_column("Quality Score", justify="right")
table.add_column("Speed Score", justify="right")
table.add_column("Weighted Total", justify="right", style="bold green")
table.add_column("Cost (ref)", justify="right", style="dim")

for rank, (key, scores) in enumerate(sorted_scores, 1):
    display_name = key.replace("-", " ").title()
    emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else ""

    table.add_row(
        f"{rank} {emoji}",
        display_name,
        f"{scores['quality']:.1f}",
        f"{scores['avg_latency']:.0f}",
        f"{scores['quality']:.1f}",
        f"{scores['speed']:.1f}",
        f"{scores['total']:.1f}",
        f"${scores['avg_cost']:.6f}",
    )

console.print(table)

# Display winner
winner_key, winner_scores = sorted_scores[0]
winner_name = winner_key.replace("-", " ").title()

console.print(f"\n[bold green]🏆 New Winner: {winner_name}[/bold green]")
console.print(f"Weighted Score: {winner_scores['total']:.1f} / 100")
console.print(f"  Quality: {winner_scores['quality']:.1f} (60% weight)")
console.print(f"  Speed: {winner_scores['speed']:.1f} (40% weight)")
console.print(f"  Cost: ${winner_scores['avg_cost']:.6f} (reference only)")

# Compare with old formula
console.print(
    "\n[bold yellow]Comparison with Old Formula (Q50%, S30%, C20%):[/bold yellow]"
)

# Old formula calculation
max_cost = max(scores["avg_cost"] for scores in weighted_scores.values()) or 0.000001

old_scores = {}
for key, metrics in avg_metrics.items():
    avg_latency = sum(metrics["latencies"]) / len(metrics["latencies"])
    avg_quality = sum(metrics["quality_scores"]) / len(metrics["quality_scores"])
    avg_cost = sum(metrics["costs"]) / len(metrics["costs"])

    speed_score = (1 - avg_latency / max_latency) * 100
    quality_score = avg_quality
    cost_score = (1 - avg_cost / max_cost) * 100

    # OLD FORMULA: Quality 50%, Speed 30%, Cost 20%
    old_weighted_total = (
        (quality_score * 0.5) + (speed_score * 0.3) + (cost_score * 0.2)
    )

    old_scores[key] = old_weighted_total

# Sort old scores
sorted_old = sorted(old_scores.items(), key=lambda x: x[1], reverse=True)

# Compare rankings
comparison_table = Table(title="Ranking Comparison", show_header=True)
comparison_table.add_column("Provider", style="magenta")
comparison_table.add_column("Old Rank", justify="center")
comparison_table.add_column("Old Score", justify="right")
comparison_table.add_column("New Rank", justify="center")
comparison_table.add_column("New Score", justify="right")
comparison_table.add_column("Change", justify="center")

old_ranking = {key: rank for rank, (key, _) in enumerate(sorted_old, 1)}
new_ranking = {key: rank for rank, (key, _) in enumerate(sorted_scores, 1)}

for key in weighted_scores.keys():
    display_name = key.replace("-", " ").title()
    old_rank = old_ranking[key]
    new_rank = new_ranking[key]
    old_score = old_scores[key]
    new_score = weighted_scores[key]["total"]

    if old_rank < new_rank:
        change = f"⬇ Down {new_rank - old_rank}"
        change_style = "red"
    elif old_rank > new_rank:
        change = f"⬆ Up {old_rank - new_rank}"
        change_style = "green"
    else:
        change = "➡ Same"
        change_style = "dim"

    comparison_table.add_row(
        display_name,
        f"#{old_rank}",
        f"{old_score:.1f}",
        f"#{new_rank}",
        f"{new_score:.1f}",
        f"[{change_style}]{change}[/{change_style}]",
    )

console.print(comparison_table)

# Check if winner changed
old_winner_key = sorted_old[0][0]
new_winner_key = sorted_scores[0][0]

if old_winner_key != new_winner_key:
    console.print("\n[bold red]⚠️ Winner Changed![/bold red]")
    console.print(f"  Old: {old_winner_key.replace('-', ' ').title()}")
    console.print(f"  New: {new_winner_key.replace('-', ' ').title()}")
else:
    console.print("\n[bold green]✅ Winner Unchanged[/bold green]")
    console.print(f"  Winner: {new_winner_key.replace('-', ' ').title()}")

console.print("\n[bold]Summary:[/bold]")
console.print("  ✅ Cost weight removed from scoring (now 0%)")
console.print("  ✅ Quality weight increased: 50% → 60%")
console.print("  ✅ Speed weight increased: 30% → 40%")
console.print("  ✅ Cost data still displayed for reference")
