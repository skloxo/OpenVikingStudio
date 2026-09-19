"""
Unit tests for Decision Bifurcation Extractor (SKILL-KD).
"""

from openviking.core.skill_kd_bifurcation import (
    AgentTrajectory,
    DecisionBifurcationExtractor,
    TrajectoryTurn,
)


def test_extract_bifurcations_turn_failure() -> None:
    student = AgentTrajectory(
        agent_id="student_7b",
        task_id="task_docker_01",
        task_description="Clean up dangling images safely",
        turns=[
            TrajectoryTurn(
                turn_idx=0,
                action_type="command",
                action_content="docker system df",
                observation="Images: 45GB, Containers: 2GB",
                is_success=True,
            ),
            TrajectoryTurn(
                turn_idx=1,
                action_type="command",
                action_content="docker rmi -f $(docker images -q)",
                observation="Error: cannot delete active image used by running container!",
                is_success=False,
            ),
        ],
        final_success=False,
    )

    teacher = AgentTrajectory(
        agent_id="teacher_opus",
        task_id="task_docker_01",
        task_description="Clean up dangling images safely",
        turns=[
            TrajectoryTurn(
                turn_idx=0,
                action_type="command",
                action_content="docker system df",
                observation="Images: 45GB, Containers: 2GB",
                is_success=True,
            ),
            TrajectoryTurn(
                turn_idx=1,
                action_type="command",
                action_content="docker image prune -f --filter 'dangling=true'",
                observation="Deleted 12 dangling images. 28GB freed.",
                is_success=True,
            ),
        ],
        final_success=True,
    )

    bifs = DecisionBifurcationExtractor.extract_bifurcations(student, teacher)
    assert len(bifs) == 1
    assert bifs[0].turn_idx == 1
    assert "docker rmi -f" in bifs[0].student_action
    assert "docker image prune" in bifs[0].teacher_action
    assert bifs[0].impact_level == "critical"

    # Generate Candidate Rules
    rules = DecisionBifurcationExtractor.generate_candidate_rules(bifs, "docker_clean")
    assert len(rules) == 1
    rule = rules[0]
    assert "DO NOT perform" in rule.rule_content
    assert "INSTEAD, execute" in rule.rule_content
    assert rule.derived_from_turn == 1
