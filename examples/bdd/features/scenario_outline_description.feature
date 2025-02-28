Feature: Basic test with parameters and description

  Scenario Outline: Test with different parameters
    The description for the scenario outline

    Given It is test with parameters
    When I have parameter <str>
    Then I emit number <parameters> on level info

    Examples:
      | str      | parameters |
      | "first"  | 123        |
      | "second" | 12345      |
