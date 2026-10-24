# The ollama HTTP API request body (ollama_via_api): the prompt on stdin, the model as the argument;
# prints the JSON body of a streamed /api/chat request.
use 5.010;
use JSON::PP;
use Encode qw(decode);

local $/; my $p = decode("UTF-8", scalar <STDIN>);
print JSON::PP->new->utf8->canonical->encode(
  { model => $ARGV[0], stream => JSON::PP::true, messages => [ { role => "user", content => $p } ] });
