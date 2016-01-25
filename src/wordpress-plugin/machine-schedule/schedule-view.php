<?php

include_once(plugin_dir_path(__FILE__) . 'options.php');
include_once(plugin_dir_path(__FILE__) . 'table.php');

class ScheduleView {

    public static function render($page_id) {
        $table = Table::get_visible($page_id);
        if (is_null($table)) {
            return "";
        }
        $machine_names = Table::get_visible_machines();
        $slot_names = Table::get_visible_slots();

        $table_html = '<h2>Live Machine Use Schedule</h2>';
        $table_html .= '<table class="machine-schedule-table"' .
            ' style="border: none; border-spacing: 0.5em;">';
        $table_html .= '<tr style="border: none;">';
        $table_html .= '<td style="border: none; width: 20%"></td>';
        foreach($slot_names as $slot_name) {
            $table_html .= "<th style='border: none;'>$slot_name</th>";
        }
        $table_html .= '</tr>';
        foreach($table as $machine_index => $slots) {
            $table_html .= '<tr style="padding: 1em;">';
            $machine_name = $machine_names[$machine_index];
            $table_html .= "<th style='border: none;'>$machine_name</th>";
            foreach($slots as $in_use) {
                if ($in_use) {
                    $class = '';
                    $style = 'background-color: #f78181;';   // red
                } else {
                    $class = '';
                    $style = 'background-color: #81f781;';   // green
                }
                $style .= 'border: none;';
                $table_html .= "<td class='$class' style='$style'></td>";
            }
            $table_html .= '</tr>';
            $machine_index++;
        }
        $table_html .= '</table>';

        return $table_html;
    }
}

?>

