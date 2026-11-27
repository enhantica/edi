"""The portrait menu renders the same leading icons as the landscape tabs."""

from pathlib import Path

import pytest
import yaml
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape

SITE = Path(__file__).resolve().parents[3] / 'website/surfaces'


@pytest.fixture
def navigation_templates():
    config = yaml.load((SITE / 'mkdocs.yml').read_text(), Loader=yaml.BaseLoader)
    env = Environment(
        loader=FileSystemLoader(SITE / 'overrides'),
        autoescape=select_autoescape(['html', 'svg']),
    )
    env.filters['url'] = str
    env.globals.update(config=config, features=config['theme']['features'])
    return (
        env.get_template('partials/nav-item.html').module.render,
        env.get_template('partials/tabs-item.html').module.render,
    )


@pytest.mark.parametrize(
    ('title', 'route', 'has_sections'),
    [
        ('Home', '/', False),
        ('User guide', '/user-guide/', True),
        ('Physics', '/physics/', True),
        ('About', '/about/', True),
        ('Application', '/application/', True),
    ],
)
def test_section_icon_is_present_in_portrait_menu(
    navigation_templates, title, route, has_sections
):
    portrait, landscape = navigation_templates
    section = {'title': title, 'url': route, 'children': [], 'active': False}
    if has_sections:
        section['children'] = [
            {**section, 'title': '', 'is_index': True},
            {**section, 'title': 'Details', 'url': route + 'detail/'},
        ]
    landscape_markup = BeautifulSoup(landscape(section), 'html.parser')
    tab = landscape_markup.select_one('.md-tabs__link')
    assert tab and tab.get_text(strip=True) == title and tab.select_one('svg path[d]'), (
        'The wide navigation tab must provide the section label and expected icon'
    )
    portrait_markup = BeautifulSoup(portrait(section, 'nav_1', 1, None), 'html.parser')
    link = portrait_markup.select_one('.md-nav__item a.md-nav__link')
    assert link and link.get_text(strip=True) == title and link['href'] == tab['href'], (
        'The portrait navigation entry must retain the matching section label and target'
    )
    assert [element['d'] for element in link.select('svg path[d]')] == [
        element['d'] for element in tab.select('svg path[d]')
    ], f'The portrait navigation entry for {title} must render the same leading icon as its tab'
