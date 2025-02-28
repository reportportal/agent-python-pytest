Feature: Four step arguments
    Description for the feature

    Scenario: Arguments for given, when, and, then
        Description for the scenario

        Given there are 5 cucumbers
            """
            Docstring for the step
            """

        When I eat 3 cucumbers
        And I eat 2 cucumbers

        Then I should have 0 cucumbers
