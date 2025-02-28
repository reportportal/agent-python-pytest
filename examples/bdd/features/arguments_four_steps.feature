Feature: Four step arguments
    Scenario: Arguments for given, when, and, then
        Given there are 5 cucumbers

        When I eat 3 cucumbers
        And I eat 2 cucumbers

        Then I should have 0 cucumbers
