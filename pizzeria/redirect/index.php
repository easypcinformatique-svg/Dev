<?php
// Fallback redirect if .htaccess is not supported
$destination = 'https://pizzanapoli-carpentras.fr' . $_SERVER['REQUEST_URI'];
header('HTTP/1.1 301 Moved Permanently');
header('Location: ' . $destination);
exit;
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0;url=https://pizzanapoli-carpentras.fr/">
    <link rel="canonical" href="https://pizzanapoli-carpentras.fr/">
    <title>Redirection - Pizza Napoli Carpentras</title>
</head>
<body>
    <p>Vous allez etre redirige vers <a href="https://pizzanapoli-carpentras.fr/">pizzanapoli-carpentras.fr</a></p>
</body>
</html>
