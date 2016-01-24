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

?>
