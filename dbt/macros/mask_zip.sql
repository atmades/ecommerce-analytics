{% macro mask_zip(column_name) %}
  CONCAT(SUBSTR({{ column_name }}, 1, 3), '**')
{% endmacro %}