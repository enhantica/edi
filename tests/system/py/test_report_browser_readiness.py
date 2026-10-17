"""Qualify report observations against delayed and undrawn independent pages."""

import pytest

from tests.fixtures.report_evolution.observe_browser import observe


@pytest.fixture(scope='module')
def independent_pages():
    html = """<!doctype html><div class="pattern-figure">
    <div id="chart" style="width:200px;height:160px"></div></div>
    <script>
    window.requestAnimationFrame = () => 0;
    const plot = document.querySelector('#chart');
    setTimeout(() => {
      plot.className = 'js-plotly-plot';
      plot.data = [{name: 'Measured', line: {color: '#0055aa'}}];
      plot.layout = {plot_bgcolor: '#ffffff'};
      if (innerWidth > 500) plot.innerHTML = '<svg width="20" height="20"></svg>';
    }, 100);
    </script>"""
    return observe(html, render_timeout_ms=250)


@pytest.mark.parametrize(
    ('view', 'drawn'),
    [('wide', True), ('narrow', False)],
    ids=['delayed-render', 'never-rendered'],
)
def test_report_observer_waits_for_drawing_without_animation_frames(
    independent_pages, view, drawn
):
    assert set(independent_pages) == {'wide', 'narrow'}, (
        'The browser observer must report each exact viewport independently of animation frames'
    )
    page = independent_pages[view]
    assert page['ready'] is drawn, (
        'Only a page with initialized plot data and an actual drawing may report ready'
    )
    assert page['patterns'][0]['traces'] == [{'name': 'Measured', 'line': {'color': '#0055aa'}}], (
        'Readiness must retain the independently declared trace and its exact colour'
    )
    assert page['errors'] == [], 'The independent delayed browser page must execute cleanly'
