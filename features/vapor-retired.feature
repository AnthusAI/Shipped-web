Feature: Vapor is retired
  Shipped does not keep a vapor log, a "No vapor" stamp or a hype gap. A claim that
  is not yet usable is listed with a neutral status, and the old Vapor log address
  sends readers to the New page.

  Background:
    Given the Shipped site is built from the fixture content

  Scenario: The Vapor log page is gone
    Then the page "/vapor/" does not exist
    And the navigation does not link to "/vapor/"

  Scenario: The old Vapor log address redirects to New
    Then the projection settings redirect "/vapor/" to "/new/"

  Scenario: No page mentions vapor or the hype gap
    Then no projected page contains "vapor"
    And no projected page contains "hype gap"
    And no projected page contains "hype-gap"

  Scenario: The masthead no longer carries the No vapor stamp
    When I open the page "/"
    Then the page does not contain "No vapor"
    And the page does not contain "brand-stamp"
