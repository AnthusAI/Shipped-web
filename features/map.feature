Feature: The map page has three views
  The map shows every tracked model as a periodic table, how concepts connect as a
  graph, and how clusters change as a river. Until items carry model details the
  table says how it will fill in.

  Background:
    Given the Shipped site is built from the fixture content

  Scenario: The map page has the title, the subtitle and the three views
    When I open the page "/map/"
    Then the page contains "The map"
    And the page contains "How the field is taking shape"
    And the page contains "Table: every model we track. Graph: how concepts connect. River: how clusters change week to week."

  Scenario: Without model details the table explains how it fills in
    When I open the page "/map/"
    Then the page contains "The table fills in as signals are tagged with their model details."

  Scenario: The map no longer claims to be the first build
    When I open the page "/map/"
    Then the page does not contain "This is the first build"
