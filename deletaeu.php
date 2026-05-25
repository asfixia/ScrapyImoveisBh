<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

// =============================
// CONFIG
// =============================
$timeout = 10;
$cacheEnabled = true;
$cacheDir = __DIR__ . '/cache';
$cacheTtl = 36000000; // 1 hour

$maxCacheSizeBytes = 5000 * 1024 * 1024; // 5 GB total
$maxFileSizeBytes = 20 * 1024 * 1024;  // 20 MB per response

// =============================
// CACHE (binary: meta JSON + raw body)
// =============================
function ensureCacheDir($dir) {
    if (!is_dir($dir)) {
        mkdir($dir, 0777, true);
    }
}

function cleanupOldCache($cacheDir, $maxCacheSizeBytes) {
    $files = glob($cacheDir . '/*.cache');

    usort($files, function ($a, $b) {
        return filemtime($a) <=> filemtime($b);
    });

    $total = 0;
    foreach ($files as $f) {
        $total += filesize($f);
    }

    foreach ($files as $f) {
        if ($total <= $maxCacheSizeBytes) {
            break;
        }
        $size = filesize($f);
        @unlink($f);
        $total -= $size;
    }
}

/**
 * Pack: 4-byte big-endian meta length + UTF-8 JSON meta + raw body bytes.
 * Meta: {"status":int,"headers":["Header: value",...]}
 */
function extract_content_type(array $headerLines) {
    foreach ($headerLines as $headerLine) {
        if (stripos($headerLine, 'content-type:') === 0) {
            return trim(substr($headerLine, 13));
        }
    }
    return null;
}

function guess_content_type($body, $url = null) {
    if ($url) {
        $path = parse_url($url, PHP_URL_PATH);
        if (is_string($path) && $path !== '') {
            $ext = strtolower(pathinfo($path, PATHINFO_EXTENSION));
            $byExt = [
                'jpg' => 'image/jpeg',
                'jpeg' => 'image/jpeg',
                'png' => 'image/png',
                'gif' => 'image/gif',
                'webp' => 'image/webp',
                'svg' => 'image/svg+xml',
                'json' => 'application/json',
                'js' => 'application/javascript',
                'css' => 'text/css; charset=utf-8',
            ];
            if (isset($byExt[$ext])) {
                return $byExt[$ext];
            }
        }
    }
    if ($body !== '') {
        $b0 = $body[0];
        if ($b0 === '{' || $b0 === '[') {
            return 'application/json; charset=utf-8';
        }
        if (strlen($body) >= 3 && substr($body, 0, 3) === "\xFF\xD8\xFF") {
            return 'image/jpeg';
        }
        if (strlen($body) >= 8 && substr($body, 0, 8) === "\x89PNG\r\n\x1a\n") {
            return 'image/png';
        }
        if (strlen($body) >= 6 && (strncmp($body, 'GIF87a', 6) === 0 || strncmp($body, 'GIF89a', 6) === 0)) {
            return 'image/gif';
        }
        if (strlen($body) >= 12 && substr($body, 0, 4) === 'RIFF' && substr($body, 8, 4) === 'WEBP') {
            return 'image/webp';
        }
    }
    return 'application/octet-stream';
}

function ensure_content_type_header(array $headers, $contentType) {
    foreach ($headers as $line) {
        if (stripos($line, 'content-type:') === 0) {
            return $headers;
        }
    }
    $headers[] = 'Content-Type: ' . $contentType;
    return $headers;
}

function cache_save($cacheFile, $status, array $headers, $body, $contentType, $targetUrl) {
    $meta = json_encode([
        'status' => (int) $status,
        'headers' => array_values($headers),
        'content_type' => $contentType,
        'url' => $targetUrl,
    ], JSON_UNESCAPED_UNICODE);
    if ($meta === false) {
        return false;
    }
    $packed = pack('N', strlen($meta)) . $meta . $body;
    return file_put_contents($cacheFile, $packed, LOCK_EX) !== false;
}

/**
 * @return array{status:int,headers:array,body:string}|null
 */
function cache_load($cacheFile) {
    $data = @file_get_contents($cacheFile);
    if ($data === false || $data === '') {
        return null;
    }

    if (strlen($data) >= 4) {
        $metaLen = unpack('N', substr($data, 0, 4))[1];
        if (
            $metaLen > 0
            && $metaLen <= 1048576
            && strlen($data) >= 4 + $metaLen
        ) {
            $meta = json_decode(substr($data, 4, $metaLen), true);
            if (
                is_array($meta)
                && isset($meta['status'])
                && is_array($meta['headers'] ?? null)
            ) {
                return [
                    'status' => (int) $meta['status'],
                    'headers' => $meta['headers'],
                    'content_type' => $meta['content_type'] ?? null,
                    'url' => $meta['url'] ?? null,
                    'body' => substr($data, 4 + $metaLen),
                ];
            }
        }
    }

    // Legacy entries: body only (no stored headers)
    return [
        'status' => 200,
        'headers' => [],
        'content_type' => null,
        'url' => null,
        'body' => $data,
    ];
}

/** Headers we must not forward (PHP sets length/chunking). */
function should_skip_response_header($headerLine) {
    $lower = strtolower($headerLine);
    return (
        strpos($lower, 'transfer-encoding:') === 0
        || strpos($lower, 'content-length:') === 0
    );
}

/**
 * Parse upstream $http_response_header; ensure Content-Type is present for cache/replay.
 * @return array{status:int,headers:array,content_type:string}
 */
function parse_upstream_response(array $http_response_header, $body, $targetUrl) {
    $status = 200;
    $stored = [];

    foreach ($http_response_header as $i => $headerLine) {
        if ($i === 0 && preg_match('#HTTP/\d+\.\d+\s+(\d+)#', $headerLine, $m)) {
            $status = (int) $m[1];
            continue;
        }
        if (should_skip_response_header($headerLine)) {
            continue;
        }
        // PHP http stream may already have decompressed the body — do not forward Content-Encoding
        $lower = strtolower($headerLine);
        if (strpos($lower, 'content-encoding:') === 0) {
            continue;
        }
        $stored[] = $headerLine;
    }

    $contentType = extract_content_type($stored);
    if ($contentType === null || $contentType === '') {
        $contentType = guess_content_type($body, $targetUrl);
        $stored = ensure_content_type_header($stored, $contentType);
    }

    return [
        'status' => $status,
        'headers' => $stored,
        'content_type' => $contentType,
    ];
}

function emit_response_headers(array $entry) {
    http_response_code((int) $entry['status']);

    $hasContentType = false;
    foreach ($entry['headers'] as $headerLine) {
        if (stripos($headerLine, 'content-type:') === 0) {
            $hasContentType = true;
        }
        if (!should_skip_response_header($headerLine)) {
            header($headerLine, false);
        }
    }

    if (!$hasContentType) {
        $contentType = $entry['content_type'] ?? null;
        if ($contentType === null || $contentType === '') {
            $contentType = guess_content_type(
                $entry['body'],
                $entry['url'] ?? null
            );
        }
        header('Content-Type: ' . $contentType);
    }
}

function apply_cors_headers() {
    header('Access-Control-Allow-Origin: *', true);
    header('Access-Control-Allow-Methods: GET, POST, OPTIONS', true);
    header('Access-Control-Allow-Headers: *', true);
}

function send_cached_response(array $entry) {
    emit_response_headers($entry);
    header('X-Cache: HIT', true);
    apply_cors_headers();
    echo $entry['body'];
}

// =============================
// CORS (responder preflight)
// =============================
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
    header('Access-Control-Allow-Headers: *');
    exit;
}

// =============================
// PEGAR URL DESTINO
// =============================
$targetUrl = null;

if (isset($_GET['url'])) {
    $targetUrl = $_GET['url'];
} else {
    $queryString = isset($_SERVER['QUERY_STRING']) ? $_SERVER['QUERY_STRING'] : '';
    if (!empty($queryString)) {
        $targetUrl = $queryString;
    }
}

if (empty($targetUrl)) {
    http_response_code(400);
    echo 'Missing target URL';
    exit;
}

$cacheFile = null;
if ($cacheEnabled) {
    ensureCacheDir($cacheDir);
    $cacheKey = md5($_SERVER['REQUEST_METHOD'] . '|' . $_SERVER['QUERY_STRING']);
    $cacheFile = "$cacheDir/$cacheKey.cache";
    if (
        file_exists($cacheFile)
        && (time() - filemtime($cacheFile)) < $cacheTtl
    ) {
        $cached = cache_load($cacheFile);
        if ($cached !== null) {
            send_cached_response($cached);
            exit;
        }
    }
}

// manter query original (exceto url)
$query = $_GET;
unset($query['url']);

if (!empty($query)) {
    $targetUrl .= (strpos($targetUrl, '?') === false ? '?' : '&') . http_build_query($query);
}

// =============================
// VALIDAR URL
// =============================
if (!filter_var($targetUrl, FILTER_VALIDATE_URL)) {
    http_response_code(400);
    echo 'Invalid URL';
    exit;
}

// =============================
// SEGURANÇA (evitar localhost)
// =============================
$parsed = parse_url($targetUrl);
$host = isset($parsed['host']) ? $parsed['host'] : '';

if (preg_match('/^(127\.|10\.|192\.168\.|localhost)/', $host)) {
    http_response_code(403);
    echo 'Blocked private address';
    exit;
}

// =============================
// COPIAR HEADERS DO CLIENTE
// =============================
$headers = [];

foreach (getallheaders() as $key => $value) {
    $k = strtolower($key);

    if (
        $k === 'host'
        || $k === 'content-length'
        || $k === 'referer'
        || $k === 'cookie'
        || (strpos($k, 'sec-') === 0)
        || (strpos($k, ':') === 0)
    ) {
        continue;
    }

    $headers[] = "$key: $value";
}

// =============================
// CONTEXTO HTTP
// =============================
$method = $_SERVER['REQUEST_METHOD'];

$options = [
    'http' => [
        'method' => $method,
        'timeout' => $timeout,
        'header' => implode("\r\n", $headers) . "\r\n",
        'ignore_errors' => true,
    ],
];

if (in_array($method, ['POST', 'PUT', 'PATCH'], true)) {
    $options['http']['content'] = file_get_contents('php://input');
}

$options['http']['follow_location'] = 1;
$options['http']['max_redirects'] = 5;

$context = stream_context_create($options);

// =============================
// FAZER REQUEST
// =============================
$response = @file_get_contents($targetUrl, false, $context);

if ($response === false) {
    http_response_code(502);
    echo 'Failed to fetch resource';
    exit;
}

$upstream = isset($http_response_header) && is_array($http_response_header)
    ? parse_upstream_response($http_response_header, $response, $targetUrl)
    : parse_upstream_response([], $response, $targetUrl);

$cacheEntry = [
    'status' => $upstream['status'],
    'headers' => $upstream['headers'],
    'content_type' => $upstream['content_type'],
    'url' => $targetUrl,
    'body' => $response,
];

if ($cacheEnabled && $cacheFile !== null && strlen($response) <= $maxFileSizeBytes) {
    cache_save(
        $cacheFile,
        $cacheEntry['status'],
        $cacheEntry['headers'],
        $response,
        $cacheEntry['content_type'],
        $targetUrl
    );
    cleanupOldCache($cacheDir, $maxCacheSizeBytes);
}

emit_response_headers($cacheEntry);
header('X-Cache: MISS', true);
apply_cors_headers();

echo $response;

?>
