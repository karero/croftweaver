# The Melious request body (run_melious): the prompt on stdin, the model and max_tokens as the
# arguments; prints the JSON body of a streamed /chat/completions request.
use 5.010;
use JSON::PP;
use Encode qw(decode);

local $/; my $p = decode("UTF-8", scalar <STDIN>);
print JSON::PP->new->utf8->canonical->encode({ model => $ARGV[0], stream => JSON::PP::true,
  stream_options => { include_usage => JSON::PP::true }, max_tokens => 0 + $ARGV[1],
  messages => [ { role => "user", content => $p } ] });
