Feature: Basic test with parameters which fails

  Scenario Outline: Test with different parameters failing
    Given It is test with parameters
    When I have parameter <str>
    Then I emit number <parameters> on level info
    Then I fail

    Examples:
      | str      | parameters |
      | "first"  | 123        |
      | "second" | 12345      |
