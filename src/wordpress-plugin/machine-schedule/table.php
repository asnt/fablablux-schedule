<?php

/**
 * Access to the table of a given page.
 */
class Table {
    private static $key = "machine_schedule_table";

    public static function get($page_id) {
        if (!is_post_type("page", $page_id)) {
            return "";
        }

        $single = true;
        $table_json = get_post_meta($page_id, self::$key, $single);
        $table = json_decode($table_json);

        return $table;
    }

    /**
     * Get the schedule with visible machines and slots only.
     *
     * @return array array("table" => array(),         // M x N
     *                     "machine_names" => array(), // M
     *                     "slot_names" => array(),    // N
     *                     )
     */
    public static function get_visible($page_id) {
        $table = Table::get($page_id);

        $options = MachineScheduleOptions::instance();
        $machine_mask = $options['visible_machines'];
        $slot_mask = $options['visible_slots'];

        $masked_table_rows = filter_rows($table, $machine_mask);
        $masked_table = filter_columns($masked_table_rows, $slot_mask);

        return $masked_table;
    }

    public static function get_visible_machines() {
        $options = MachineScheduleOptions::instance();
        $machine_names = $options['machine_names'];
        $machine_mask = $options['visible_machines'];

        $masked_machine_names = filter_rows($machine_names, $machine_mask);

        return $masked_machine_names;
    }

    public static function get_visible_slots() {
        $options = MachineScheduleOptions::instance();
        $slot_names = $options['slot_names'];
        $slot_mask = $options['visible_slots'];

        $masked_slot_names = filter_rows($slot_names, $slot_mask);

        return $masked_slot_names;
    }

    public static function update($page_id, $table) {
        if (!is_post_type("page", $page_id)) {
            return false;
        }

        $json_table = json_encode($table);
        $result = update_post_meta($page_id, self::$key, $json_table);
        // $result is true or integer on success. Convert to a boolean return
        // value.
        $success = $result != false;

        return $success;
    }
}

/**
 * Check if a post is of of a given type.
 *
 * @param string $type The post type.
 * @param int $post_id
 *
 * @return bool True if the requested type matched the post.
 */
function is_post_type($type, $post_id) {
    $post = get_post($post_id);
    if (is_null($post)) {
        return false;
    }
    return $post->post_type == $type;
}

/**
 * Filter the rows of an array using the given mask.
 *
 * The mask must be the same length as the number of rows in the array. If
 * not, the $array is returned as is.
 *
 * @return array
 */
function filter_rows($array, $row_mask) {
    $n_rows = count($array);
    if ($n_rows != count($row_mask)) {
        return $array;
    }

    $filtered_array = array();

    for($index = 0; $index < $n_rows; $index++) {
        if($row_mask[$index]) {
            array_push($filtered_array, $array[$index]);
        }
    }

    return $filtered_array;
}

/**
 * Filter the columns of an array using the given mask.
 *
 * The mask must be the same length as the number of columns in the array.
 * If not, the $array is returned as is.
 *
 * @return array
 */
function filter_columns($array, $col_mask) {
    $n_rows = count($array);
    if($n_rows == 0) {
        return $array;
    }

    $n_cols = count($array[0]);
    if ($n_cols != count($col_mask)) {
        return $array;
    }

    $filtered_array = array();

    for($row = 0; $row < $n_rows; $row++) {
        $row_array = array();
        for($col = 0; $col < $n_cols; $col++) {
            if($col_mask[$col]) {
                array_push($row_array, $array[$row][$col]);
            }
        }
        array_push($filtered_array, $row_array);
    }

    return $filtered_array;
}

?>
