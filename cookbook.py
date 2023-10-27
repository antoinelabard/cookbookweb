#!/usr/bin/python3

"""
NAME
    cookbook.py - Generate custom meals.

SYNOPSIS
    ./cookbook.py [OPTION]...

DESCRIPTION
    cookbook.py is intended to generate a random menu matching some filters. Those filters can be given as command line
    arguments, but they also can be given via profiles defines in the script. This script is used to make sure that no
    human mind is involved in the random generation of menus, as it is bad at randomness and risks promote some recipes
    over others. The idea is to randomly pick the recipes matching the provided filters using a draw without discount
    and bet on the equiprobability of each recipe to be chosen in order to statistically select every recipe over time.

CONFIGURATION
    cookbook.py can take several arguments:
        - export: create a markdown file containing wikilinks for all the recipes of the cookbook. It can be read using
        Obsidian (https://obsidian.md).
        - plan=PLAN: generate a menu following the filters pointed by PLAN (defined in the script)
        - filter=VALUE: set a custom filter that the recipes need to match. Here is the list of filters with their
        expected value:
            - type: "meal"|"ingredient"|"inedible"
            - opportunity: None|"cheat-meal"|"party"|"pleasure"
            - lunch: integer
            - breakfast: integer
            - snack: integer
            - appetizer: integer
"""
from __future__ import annotations
import sys
from enum import Enum
from typing import Dict, Any, Tuple, List, Callable

import yaml
import math
import random
from pathlib import Path


class Tag(str, Enum):
    APPETIZER: str = "appetizer"
    BREAKFAST: str = "breakfast"
    COOKED_DATES: str = "cooked dates"
    FILTERS: str = "filters"
    LUNCH: str = "lunch"
    MEAL: str = "meal"
    OPPORTUNITY: str = "opportunity"
    NB_PEOPLE: str = "nb_people"
    PLAN: str = "plan"
    RECIPES: str = "recipes"
    SNACK: str = "snack"
    TYPE: str = "type"


class Options(int, Enum):
    NB_PORTIONS_PER_RECIPE: int = 4  # I plan to set the number of portions for each recipe
    NB_LUNCHES_PER_DAY: int = 2
    NB_BREAKFASTS_PER_DAY: int = 1
    NB_SNACKS_PER_DAY: int = 1


def singleton(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


@singleton
class CookBookRepository:
    """
    CookBookRepository: Manage the access to the data stored in the cookbook. Any read or write operation must be
        handled by this class. It includes operations to read the general cookbook metadata and the metadata of each of
        the recipes.
    """

    ROOT_DIR: Path = Path(__file__).parent
    RECIPE_DIR: Path = ROOT_DIR / "recettes"
    COMPLETE_COOKBOOK_PATH: Path = ROOT_DIR / "cookbook.md"
    MENU_PATH: Path = ROOT_DIR / "menu.md"
    RECIPE_DICT: Dict[str, Path] = {path.stem: path for path in RECIPE_DIR.iterdir() if path.is_file()}
    RECIPE_NAMES: Tuple[str] = tuple([recipe_name for recipe_name in RECIPE_DICT.keys()])

    RECIPE_METADATA_TEMPLATE = {
        Tag.COOKED_DATES: []
    }
    # add a pagebreak web inserted in a markdown document
    PAGEBREAK: str = '\n\n<div style="page-break-after: always;"></div>\n\n'

    def __init__(self):
        self.recipes_metadata = self._read_recipes_metadata()

    def get_recipes_cooked_dates(self):
        recipes_cooked_dates: Dict[str, Any] = {}
        for recipe_name, metadata in self.cookbook_metadata.items():
            recipes_cooked_dates[recipe_name] = metadata[self.COOKED_DATES]
        return recipes_cooked_dates

    @classmethod
    def _read_metadata_from_md(cls, path: Path) -> str | Dict[str, str]:
        """
        :param path: the path to the markdown file containing the metadata
        :return: an empty string if there is no metadata in the file. Otherwise, return a dictionary of the metadata
        """
        lines: str = ""
        metadata_marker: str = "---\n"
        with open(path, 'r') as f:
            line: str = f.readline()
            if line != metadata_marker:  # check if there is metadata in the file
                return ""
            while True:
                line = f.readline()
                if line == metadata_marker:
                    return yaml.safe_load(lines)
                lines += line

    def _read_recipes_metadata(self) -> Dict[str, str | Dict[str, str]]:
        """
        :return: the metadata of all the files in a dictionary
        """
        files_metadata: Dict[str, str | Dict[str, str]] = {}
        for recipe_name, recipe_path in self.RECIPE_DICT.items():
            file_metadata = self._read_metadata_from_md(recipe_path)
            if file_metadata != '':
                files_metadata[recipe_name] = file_metadata
        return files_metadata

    def read_menu(self):
        """
        Read the menu referred by MENU_PATH and return a list of all the recipes contained in it.
        """
        with open(self.MENU_PATH, 'r') as f:
            lines: List[str] = f.readlines()
        recipes_names: List[str] = list(map(lambda line: line.replace("![[", "").replace("]]\n", ""), lines))
        recipes_names = [recipe_name for recipe_name in recipes_names if recipe_name in self.RECIPE_DICT]
        return recipes_names

    def write_menu(self, meal_plan: MealPlan) -> None:
        menu_str: str = f"""# Menu
                
            """
        meal_str: str = """## {}
            
            {}
            
            """
        to_str: Callable[[List[str]], str] = lambda l: self.PAGEBREAK.join([f"![[{i}]]" for i in l])

        for meal, recipes in meal_plan.__dict__.items():
            menu_str += meal_str.format(meal, to_str(recipes))
        menu_str = menu_str.replace("    ", "")
        print(menu_str)
        with open(self.MENU_PATH, 'w') as f:
            f.write(menu_str)

    def export_complete_cookbook(self):
        """
        create a document containing quotes of the recipes contained in the cookbook.
        """

        complete_cookbook_template = """# Livre de recettes
        
            {}""".replace("    ", "")

        files_wikilinks = [f'![[{file}]]' for file in self.RECIPE_NAMES]

        with open(self.COMPLETE_COOKBOOK_PATH, 'w') as f:
            f.write(complete_cookbook_template.format(self.PAGEBREAK.join(files_wikilinks)))


class MealPlan:
    def __init__(self, lunch_list, breakfast_list, snack_list, appetizer_list):
        self.lunch = lunch_list
        self.breakfast = breakfast_list
        self.snack = snack_list
        self.appetizer = appetizer_list


class MealGenerator:
    """
    MealGenerator: Used to generate a new meal plan, given a certain profile established in advance. This class is
    intended to generate meals plan based on the prior cook history of the cookbook. It uses the cookbook metadata
    cooked dates to determine the least cooked recipes matching the indicated filters, and pick among the candidates
    to return the result.
    """

    def __init__(self, recipe_type: str, opportunity: None | str, nb_lunch: int, nb_breakfast: int, nb_snack: int,
                 nb_appetizers: int):
        self.repository: CookBookRepository = CookBookRepository()

        self.meals: Dict[str, int] = {
            Tag.LUNCH: nb_lunch,
            Tag.BREAKFAST: nb_breakfast,
            Tag.SNACK: nb_snack,
            Tag.APPETIZER: nb_appetizers
        }

        # each filter must be an instance of str, list(str) or None
        self.filters: Dict[str, str | List[str] | None] = {
            Tag.TYPE: recipe_type,
            Tag.OPPORTUNITY: opportunity
        }

    def _match_filters(self, recipe_name: str) -> bool:
        for filter_name in set(self.filters.keys()):
            filter_name = filter_name.value
            if filter_name not in self.repository.recipes_metadata[recipe_name]:
                continue

            if self.filters[filter_name] is None:
                return False

            if self.filters[filter_name] != self.repository.recipes_metadata[recipe_name][filter_name]:
                return False

        return True

    def _match_meal(self, name: str, meal: str) -> bool:
        if Tag.MEAL not in self.repository.recipes_metadata[name]:
            return False
        return self.repository.recipes_metadata[name][Tag.MEAL] == meal

    def generate_meal_plan(self, nb_people: int = 1):
        recipes_names_filtered: List[str] = [name for name in self.repository.RECIPE_NAMES if self._match_filters(name)]
        meal_plan: Dict[str, List[str]] = {}
        for meal, quantity in self.meals.items():
            if quantity == 0:
                meal_plan[meal]: List[str] = []
                continue
            total_quantity: int = quantity * nb_people

            rcp_names: List[str] = [name for name in recipes_names_filtered if self._match_meal(name, meal)]

            if len(rcp_names) == 0:
                continue

            rcp_nm: List[str] = rcp_names.copy()

            meal_plan_per_meal: List[str] = []

            while total_quantity > 0:
                index: int = random.randint(0, len(rcp_nm) - 1)
                meal_plan_per_meal.append(rcp_nm.pop(index))
                total_quantity -= 1

                if len(rcp_nm) == 0:
                    rcp_nm = rcp_names.copy()

            meal_plan[meal] = meal_plan_per_meal
        self.repository.write_menu(
            MealPlan(
                meal_plan[Tag.LUNCH],
                meal_plan[Tag.BREAKFAST],
                meal_plan[Tag.SNACK],
                meal_plan[Tag.APPETIZER]
            )
        )


def process_arguments():
    args = {
        Tag.TYPE: Tag.MEAL,
        Tag.LUNCH: 0,
        Tag.BREAKFAST: 0,
        Tag.SNACK: 0,
        Tag.APPETIZER: 0,
        Tag.OPPORTUNITY: None,
        Tag.NB_PEOPLE: 1
    }
    for arg in sys.argv:
        if "export" in arg:
            CookBookRepository().export_complete_cookbook()
            return
        if "plan" in arg:
            plan = arg.split('=')[-1]
            if plan == "week":
                args[Tag.TYPE] = Tag.MEAL
                args[Tag.OPPORTUNITY] = None
                args[Tag.LUNCH] = math.ceil(7 * Options.NB_LUNCHES_PER_DAY / Options.NB_PORTIONS_PER_RECIPE)
                print(math.ceil(7 * Options.NB_LUNCHES_PER_DAY / Options.NB_PORTIONS_PER_RECIPE))
                args[Tag.BREAKFAST] = math.ceil(7 * Options.NB_BREAKFASTS_PER_DAY / Options.NB_PORTIONS_PER_RECIPE)
                args[Tag.SNACK] = math.ceil(7 * Options.NB_SNACKS_PER_DAY / Options.NB_PORTIONS_PER_RECIPE)
                args[Tag.APPETIZER] = 0
        if '=' in arg:
            s = arg.split('=')
            args[s[0]] = s[-1]
    MealGenerator(
        recipe_type=args[Tag.TYPE],
        opportunity=args[Tag.OPPORTUNITY],
        nb_lunch=int(args[Tag.LUNCH]),
        nb_breakfast=int(args[Tag.BREAKFAST]),
        nb_snack=int(args[Tag.SNACK]),
        nb_appetizers=int(args[Tag.APPETIZER]),
    ).generate_meal_plan(int(args[Tag.NB_PEOPLE]))


if __name__ == "__main__":
    process_arguments()
