Feature: Dynamic scenario outline names

  Scenario Outline: Test with the parameter <str>
    Given It is test with parameters
    When I have parameter <str>
    Then I emit number <parameters> on level info

    Examples:
      | str      | parameters |
      | "first"  | 123        |
      | "second" | 12345      |
