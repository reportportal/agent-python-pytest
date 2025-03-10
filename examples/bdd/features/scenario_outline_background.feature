Feature: Basic test with parameters and background

  Background:
    Given I have empty step in background

  Scenario Outline: Test with different parameters
    Given It is test with parameters
    When I have parameter <str>
    Then I emit number <parameters> on level info

    Examples:
      | str      | parameters |
      | "first"  | 123        |
      | "second" | 12345      |
