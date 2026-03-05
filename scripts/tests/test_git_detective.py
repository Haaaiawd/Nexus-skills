"""
tests/test_git_detective.py — git_detective.py 单元测试

覆盖：hotspot 计算、coupling 计算、风险阈值、边界案例（单文件commit/空历史）
注意：git 调用用 mock 隔离，不依赖真实 repo。
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# conftest.py 已将 scripts/ 加入 sys.path
from git_detective import (
    compute_hotspots,
    compute_coupling_pairs,
    get_commit_file_changes,
    get_repo_stats,
)


# ─────────────────────────────────────────
# compute_hotspots
# ─────────────────────────────────────────

def test_hotspots_sorted_descending():
    commits = [
        ['a.py', 'b.py'],
        ['a.py', 'c.py'],
        ['a.py'],
    ]
    result = compute_hotspots(commits, top_n=10)
    changes = [r['changes'] for r in result]
    assert changes == sorted(changes, reverse=True)


def test_hotspots_counts_correctly():
    commits = [['a.py', 'b.py'], ['a.py']]
    result = compute_hotspots(commits, top_n=10)
    a = next(r for r in result if r['path'] == 'a.py')
    b = next(r for r in result if r['path'] == 'b.py')
    assert a['changes'] == 2
    assert b['changes'] == 1


def test_hotspots_top_n_respected():
    commits = [[f'file{i}.py'] for i in range(20)]
    result = compute_hotspots(commits, top_n=5)
    assert len(result) <= 5


def test_hotspots_empty_commits():
    assert compute_hotspots([], top_n=10) == []


# ─────────────────────────────────────────
# 风险阈值
# ─────────────────────────────────────────

def test_risk_low():
    commits = [['x.py']] * 4  # changes=4
    result = compute_hotspots(commits, top_n=1)
    assert result[0]['risk'] == 'low'


def test_risk_medium_boundary():
    commits = [['x.py']] * 5  # changes=5 → medium
    result = compute_hotspots(commits, top_n=1)
    assert result[0]['risk'] == 'medium'


def test_risk_high_boundary():
    commits = [['x.py']] * 15  # changes=15 → high
    result = compute_hotspots(commits, top_n=1)
    assert result[0]['risk'] == 'high'


def test_risk_medium_upper():
    commits = [['x.py']] * 14  # changes=14 → medium
    result = compute_hotspots(commits, top_n=1)
    assert result[0]['risk'] == 'medium'


# ─────────────────────────────────────────
# compute_coupling_pairs
# ─────────────────────────────────────────

def test_coupling_detected():
    # a.py 和 b.py 在 2 个 commit 里同时出现
    commits = [
        ['a.py', 'b.py'],
        ['a.py', 'b.py'],
        ['c.py'],
    ]
    result = compute_coupling_pairs(commits, top_n=10)
    assert len(result) == 1
    pair = result[0]
    assert {pair['file_a'], pair['file_b']} == {'a.py', 'b.py'}
    assert pair['co_changes'] == 2


def test_coupling_score_calculation():
    # a.py: 3 changes, b.py: 3 changes, co-changes: 2
    # score = 2 / min(3, 3) = 0.667
    commits = [
        ['a.py', 'b.py'],
        ['a.py', 'b.py'],
        ['a.py'],
        ['b.py'],
    ]
    result = compute_coupling_pairs(commits, top_n=10)
    pair = next(r for r in result if {r['file_a'], r['file_b']} == {'a.py', 'b.py'})
    assert abs(pair['coupling_score'] - round(2/3, 3)) < 0.001


def test_coupling_filters_single_co_change():
    """co_changes < 2 的对不应该出现"""
    commits = [
        ['a.py', 'b.py'],  # 只一次
        ['a.py'],
        ['b.py'],
    ]
    result = compute_coupling_pairs(commits, top_n=10)
    assert result == []


def test_coupling_empty_commits():
    assert compute_coupling_pairs([], top_n=10) == []


def test_no_coupling_for_single_file_commits():
    """每次 commit 只有 1 个文件，不会产生 coupling"""
    commits = [['a.py'], ['b.py'], ['a.py'], ['b.py']]
    result = compute_coupling_pairs(commits, top_n=10)
    assert result == []


def test_coupling_top_n_respected():
    # 生成 10 个文件，两两配对产生大量耦合对
    files = [f'f{i}.py' for i in range(10)]
    commits = [files] * 5  # 所有文件在 5 个 commit 里都出现
    result = compute_coupling_pairs(commits, top_n=3)
    assert len(result) <= 3


# ─────────────────────────────────────────
# get_commit_file_changes（mock git）
# ─────────────────────────────────────────

GIT_LOG_OUTPUT = """COMMIT:abc123
src/main.py
src/utils.py
COMMIT:def456
src/main.py
tests/test_main.py
COMMIT:ghi789
README.md
"""


def test_parse_commit_file_changes(tmp_path):
    with patch('git_detective.run_git', return_value=GIT_LOG_OUTPUT):
        commits = get_commit_file_changes(tmp_path, days=90)
    assert len(commits) == 3
    assert 'src/main.py' in commits[0]
    assert 'src/utils.py' in commits[0]
    assert 'src/main.py' in commits[1]
    assert 'tests/test_main.py' in commits[1]
    assert 'README.md' in commits[2]


def test_parse_empty_git_log(tmp_path):
    with patch('git_detective.run_git', return_value=''):
        commits = get_commit_file_changes(tmp_path, days=90)
    assert commits == []


# ─────────────────────────────────────────
# get_repo_stats（mock git）
# ─────────────────────────────────────────

def test_repo_stats_counts(tmp_path):
    commit_hashes = '\n'.join([f'hash{i}' for i in range(5)])
    author_emails = 'alice@x.com\nbob@x.com\nalice@x.com\n'

    with patch('git_detective.run_git', side_effect=[commit_hashes, author_emails]):
        stats = get_repo_stats(tmp_path, days=90)

    assert stats['total_commits'] == 5
    assert stats['total_authors'] == 2


def test_repo_stats_git_failure(tmp_path):
    with patch('git_detective.run_git', side_effect=RuntimeError('git failed')):
        stats = get_repo_stats(tmp_path, days=90)
    assert stats['total_commits'] == 0
    assert stats['total_authors'] == 0
