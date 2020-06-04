# Basics of Elliptic Curve Cryptography
import collections


def inv(n, q):
    """div on PN modulo a/b mod q as a * inv(b, q) mod q
    >>> assert n * inv(n, q) % q == 1
    """
    for i in range(q):
        if (n * i) % q == 1:
            return i
        pass
    assert False, "unreached"
    pass


def sqrt(n, q):
    """sqrt on PN modulo: it may not exist
    >>> assert (sqrt(n, q) ** 2) % q == n
    """
    assert n < q
    for i in range(1, q):
        if i * i % q == n:
            return (i, q - i)
        pass
    raise Exception("not found")


Coord = collections.namedtuple("Coord", ["x", "y"])


class EC(object):
    """System of Elliptic Curve"""
    def __init__(self, a, b, q):
        """elliptic curve as: (y**2 = x**3 + a * x + b) mod q
        - a, b: params of curve formula
        - q: prime number
        """
        assert 0 < a and a < q and 0 < b and b < q and q > 2
        assert (4 * (a ** 3) + 27 * (b ** 2))  % q != 0
        self.a = a
        self.b = b
        self.q = q
        # just as unique ZERO value representation for "add": (not on curve)
        self.zero = Coord(0, 0)
        pass

    def is_valid(self, p):
        if p == self.zero: return True
        l = (p.y ** 2) % self.q
        r = ((p.x ** 3) + self.a * p.x + self.b) % self.q
        return l == r

    def at(self, x):
        """find points on curve at x
        - x: int < q
        - returns: ((x, y), (x,-y)) or not found exception
        >>> a, ma = ec.at(x)
        >>> assert a.x == ma.x and a.x == x
        >>> assert a.x == ma.x and a.x == x
        >>> assert ec.neg(a) == ma
        >>> assert ec.is_valid(a) and ec.is_valid(ma)
        """
        assert x < self.q
        ysq = (x ** 3 + self.a * x + self.b) % self.q
        y, my = sqrt(ysq, self.q)
        return Coord(x, y), Coord(x, my)

    def neg(self, p):
        """negate p
        >>> assert ec.is_valid(ec.neg(p))
        """
        return Coord(p.x, -p.y % self.q)

    def add(self, p1, p2):
        """<add> of elliptic curve: negate of 3rd cross point of (p1,p2) line
        >>>  c = ec.add(a, b)
        >>> assert ec.is_valid(a)
        >>> assert ec.add(c, ec.neg(b)) == a
        """
        if p1 == self.zero: return p2
        if p2 == self.zero: return p1
        if p1.x == p2.x and p1.y != p2.y:
            # p1 + -p1 == 0
            return self.zero
        if p1.x == p2.x:
            # p1 + p1: use tangent line of p1 as (p1,p1) line
            l = (3 * p1.x * p1.x + self.a) * inv(2 * p1.y, self.q) % self.q
            pass
        else:
            l = (p2.y - p1.y) * inv(p2.x - p1.x, self.q) % self.q
            pass
        x = (l * l - p1.x - p2.x) % self.q
        y = (l * (p1.x - x) - p1.y) % self.q
        return Coord(x, y)

    def mul(self, p, n):
        """n times <mul> of elliptic curve
        >>> m = ec.mul(n, p)
        >>> assert ec.is_valid(m)
        """
        r = self.zero
        for i in range(n):
            r = self.add(r, p)
            pass
        return r
    pass


class ElGamal(object):
    """El Gamal Encryption
    pub key encryption as replacing (mulmod, powmod) to (ec.add, ec.mul)
    """
    def __init__(self, ec):
        self.ec = ec
        pass

    def gen(self, priv, pub1):
        """generate pub key
        - priv: priv key as (random) int < ec.q
        - pub1: (random) a point on ec
        - returns: pub key as (pub1, pub2) as points on ec
        """
        assert self.ec.is_valid(pub1)
        return (pub1, self.ec.mul(pub1, priv))

    def enc(self, plain, pub, r):
        """encrypt
        - plain: data as a point on ec
        - pub: pubkey as (pub1, pub2) as points on ec
        - r: randam int < ec.q
        - returns: (cipher1, ciper2) as points on ec
        """
        assert self.ec.is_valid(plain)
        return (self.ec.mul(pub[0], r), 
                self.ec.add(plain, self.ec.mul(pub[1], r)))

    def dec(self, cipher, priv):
        """decrypt
        - chiper: (chiper1, chiper2) as points on ec
        - priv: private key as int < ec.q
        - returns: plain as a point on ec
        """
        return self.ec.add(cipher[1], 
                           self.ec.neg(self.ec.mul(cipher[0], priv)))
    pass

class ECDH(object):
    """Elliptic Curve Diffie Hellman (Key Agreement)
    """
    def __init__(self, ec, g):
        assert ec.is_valid(g)
        self.ec = ec
        self.g=g
        pass

    def gen(self, priv):
        """generate pub key"""
        return self.ec.mul(self.g, priv)

    def secret(self, priv, pub):
        """calc secret key for the pair"""
        assert self.ec.is_valid(pub)
        return self.ec.mul(pub, priv)
    pass


if __name__ == "__main__":
    # enc/dec usage
    ec = EC(1, 18, 19)
    eg = ElGamal(ec)
    priv = 5
    pub1, _ = ec.at(7)
    plain, _ = ec.at(1)
    
    pub = eg.gen(priv, pub1)
    cipher = eg.enc(plain, pub, 15)
    decoded = eg.dec(cipher, priv)
    assert decoded == plain
    assert cipher != pub
    
    # ecdh usage
    g, _ = ec.at(7) # shared
    ecdh = ECDH(ec, g)
    
    apriv = 15
    apub = ecdh.gen(apriv)
    
    bpriv = 3
    bpub = ecdh.gen(bpriv)
    
    cpriv = 7
    cpub = ecdh.gen(cpriv)
    # same secret on each pair
    assert ecdh.secret(apriv, bpub) == ecdh.secret(bpriv, apub)
    assert ecdh.secret(apriv, cpub) == ecdh.secret(cpriv, apub)
    assert ecdh.secret(bpriv, cpub) == ecdh.secret(cpriv, bpub)
    
    # not same secret on other pair
    assert ecdh.secret(apriv, cpub) != ecdh.secret(apriv, bpub)
    assert ecdh.secret(bpriv, apub) != ecdh.secret(bpriv, cpub)
    assert ecdh.secret(cpriv, bpub) != ecdh.secret(cpriv, apub)
    pass
