Feature: Basic test with parameters

  @tc_id:outline_tc_id
  Scenario Outline: Test with different parameters
    Given It is test with parameters
    When I have parameter <str>
    Then I emit number <parameters> on level info

    Examples:
      | str      | parameters |
      | "first"  | 123        |
